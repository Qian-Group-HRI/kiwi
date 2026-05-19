"""
KIWI Control Center — Final Version
Auto-push episodes to HF on save. Camera swap. Polished UI.
http://localhost:5000
"""
import json,os,sys,time,math,threading,shutil,glob
from pathlib import Path
from datetime import datetime
from flask import Flask,render_template_string,jsonify,request,Response
from flask_socketio import SocketIO

sys.path.insert(0,os.path.join(os.path.dirname(__file__),"src"))
try: import scservo_sdk as scs; HAS_SDK=True
except: HAS_SDK=False
try:
    from lerobot.robots.so101_follower import SO101Follower
    from lerobot.robots.so101_follower.config_so101_follower import SO101FollowerConfig
    from lerobot.teleoperators.so101_leader import SO101Leader
    from lerobot.teleoperators.so101_leader.config_so101_leader import SO101LeaderConfig
    HAS_LEROBOT=True
except: HAS_LEROBOT=False
try: import cv2; HAS_CV2=True
except: HAS_CV2=False

app=Flask(__name__);app.config["SECRET_KEY"]="kiwi"
socketio=SocketIO(app,cors_allowed_origins="*")
JOINTS=["shoulder_pan","shoulder_lift","elbow_flex","wrist_flex","wrist_roll","gripper"]
port_lock=threading.Lock()

state={"leader_port":"","follower_port":"","teleop_running":False,
    "stop_event":threading.Event(),"temp_history":{n:[] for n in JOINTS},"busy":False}
try:
    with open(".ports.json") as f:c=json.load(f);state["leader_port"]=c.get("leader","");state["follower_port"]=c.get("follower","")
except: pass

rec={"active":False,"frames":[],"count":0,"t0":0,"ep_num":0,"saved":0,"ep_dir":None,
     "target":50,"ds_name":"so101_pick_place","task":"Pick object and place in box",
     "repo":"G3nadh/so101_pick_place","pending":False,"preview_frames":{},
     "auto_push":True}

# ═══ CAMERAS ═══
cam_info={}; latest_frames={}; caps={}

def cam_reader(idx):
    while True:
        if idx in caps:
            ret,frame=caps[idx].read()
            if ret: latest_frames[idx]=frame
        time.sleep(0.015)

def init_cameras():
    if not HAS_CV2: return
    labels=["Gripper","Overhead","Camera 2","Camera 3","Camera 4"]
    found=0
    for idx in range(10):
        cap=cv2.VideoCapture(idx)
        if cap.isOpened():
            ret,_=cap.read()
            if ret:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH,640);cap.set(cv2.CAP_PROP_FRAME_HEIGHT,480);cap.set(cv2.CAP_PROP_FPS,30)
                name=labels[found] if found<len(labels) else f"Camera {found}"
                cam_info[idx]=name;caps[idx]=cap
                threading.Thread(target=cam_reader,args=(idx,),daemon=True).start()
                print(f"  Camera {idx} ({name}): streaming");found+=1
            else: cap.release()
        else: cap.release()
    time.sleep(1)

def gen_mjpeg(idx):
    while True:
        if idx in latest_frames:
            _,buf=cv2.imencode('.jpg',latest_frames[idx],[cv2.IMWRITE_JPEG_QUALITY,75])
            yield(b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'+buf.tobytes()+b'\r\n')
        time.sleep(0.04)

def gen_preview(idx):
    files=rec["preview_frames"].get(idx,[])
    if not files: return
    while True:
        for fp in files:
            try:
                with open(fp,"rb") as f: data=f.read()
                yield(b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'+data+b'\r\n')
            except: pass
            time.sleep(0.05)
        time.sleep(0.5)

# ═══ SERVOS ═══
def auto_detect_ports():
    if not HAS_SDK: return []
    try:
        import serial.tools.list_ports;ports=[p.device for p in serial.tools.list_ports.comports()]
    except: return []
    found=[]
    for port in ports:
        try:
            with port_lock:
                p=scs.PortHandler(port)
                if not p.openPort(): continue
                p.setBaudRate(1000000);pkt=scs.PacketHandler(0);ok=False
                for _ in range(3):
                    _,result,_=pkt.ping(p,1)
                    if result==0:ok=True;break
                    time.sleep(0.1)
                p.closePort()
                if ok:found.append(port)
        except:
            try:p.closePort()
            except:pass
    return found

def read_servos(port):
    if not HAS_SDK or not port or state["busy"]: return None
    try:
        with port_lock:
            p=scs.PortHandler(port);p.openPort();p.setBaudRate(1000000);pkt=scs.PacketHandler(0);data=[]
            for i,n in enumerate(JOINTS):
                sid=i+1;pos,_,_=pkt.read2ByteTxRx(p,sid,56);time.sleep(.03)
                tmp,_,_=pkt.read1ByteTxRx(p,sid,63);time.sleep(.03)
                data.append({"name":n,"position":pos,"temp":tmp,"pct":round((pos/4095)*100,1)})
                state["temp_history"][n].append(tmp)
                if len(state["temp_history"][n])>60:state["temp_history"][n].pop(0)
            p.closePort();return data
    except: return None

def run_gesture(port,gn):
    state["busy"]=True
    try:
        with port_lock:
            p=scs.PortHandler(port);p.openPort();p.setBaudRate(1000000);pkt=scs.PacketHandler(0)
            def rc():
                c=[]
                for sid in range(1,7):pos,_,_=pkt.read2ByteTxRx(p,sid,56);time.sleep(.02);c.append(pos)
                return c
            def mv(tgt,dur=1.5):
                c=rc()
                for sid in range(6):pkt.write2ByteTxRx(p,sid+1,42,c[sid]);time.sleep(.02)
                for sid in range(1,7):pkt.write1ByteTxRx(p,sid,40,1);time.sleep(.02)
                steps=max(10,int(dur*25))
                for s in range(1,steps+1):
                    t=s/steps;t=t*t*(3-2*t)
                    for sid in range(6):pkt.write2ByteTxRx(p,sid+1,42,int(c[sid]+(tgt[sid]-c[sid])*t))
                    time.sleep(dur/steps)
            H=[2048,870,3088,2841,2048,2030]
            if gn=="wave":
                mv([2048,1400,1400,1600,2048,2800],1.0)
                for _ in range(3):mv([2048,1400,1400,1600,2500,2800],0.3);mv([2048,1400,1400,1600,1600,2200],0.3)
                mv(H,1.0)
            elif gn=="nod":
                mv([2048,1600,1800,1800,2048,2048],0.8)
                for _ in range(3):mv([2048,1800,2000,1600,2048,2048],0.3);mv([2048,1400,1600,2000,2048,2048],0.3)
                mv(H,0.8)
            elif gn=="shake":
                mv([2048,1600,1800,2048,2048,2048],0.8)
                for _ in range(3):mv([1700,1600,1800,2048,2048,2048],0.3);mv([2400,1600,1800,2048,2048,2048],0.3)
                mv(H,0.8)
            elif gn=="thumbsup":mv([2048,1400,1400,1600,2048,2800],1.5);time.sleep(1.5);mv(H,1.5)
            elif gn=="point":mv([2048,1400,1400,2048,2048,2048],1.5);time.sleep(1.5);mv(H,1.5)
            elif gn=="dance":
                mv([2048,1600,1800,1800,2048,2400],1.0)
                for tv in range(120):
                    a=tv*2*math.pi/30;e=math.sin(tv/120*math.pi)
                    ps=[int(2048+e*300*math.sin(a)),int(1600+e*200*math.sin(a-.8)),int(1800+e*250*math.cos(a)),int(1800+e*200*math.sin(a-2)),int(2048+e*350*math.sin(a*1.5)),int(2400+e*200*math.sin(a*1.2))]
                    for sid,pos in enumerate(ps,1):pkt.write2ByteTxRx(p,sid,42,pos)
                    time.sleep(.04)
                mv(H,1.5)
            elif gn=="home":mv(H,2.0)
            for sid in range(1,7):pkt.write1ByteTxRx(p,sid,40,0);time.sleep(.02)
            p.closePort()
    except Exception as e:
        try:p.closePort()
        except:pass
        socketio.emit("err",{"e":str(e)})
    state["busy"]=False

# ═══ DATASET ═══
def record_worker():
    rec["t0"]=time.time();rec["frames"]=[];rec["count"]=0;rec["preview_frames"]={}
    ep_dir=rec["ep_dir"]
    for idx in cam_info:(ep_dir/f"cam_{idx}").mkdir(parents=True,exist_ok=True)
    while rec["active"]:
        fi=rec["count"]
        for idx in cam_info:
            if idx in latest_frames:
                cv2.imwrite(str(ep_dir/f"cam_{idx}/{fi:06d}.jpg"),latest_frames[idx])
        try:
            obs={}
            with port_lock:
                p=scs.PortHandler(state["follower_port"]);p.openPort();p.setBaudRate(1000000);pkt=scs.PacketHandler(0)
                for i,n in enumerate(JOINTS):pos,_,_=pkt.read2ByteTxRx(p,i+1,56);obs[n]=pos
                p.closePort()
        except:pass
        rec["frames"].append({"t":round(time.time()-rec["t0"],4),"i":fi,"pos":obs})
        rec["count"]+=1
        socketio.emit("rec_tick",{"f":rec["count"],"t":round(time.time()-rec["t0"],1)})
        time.sleep(0.033)
    for idx in cam_info:
        files=sorted(glob.glob(str(ep_dir/f"cam_{idx}/*.jpg")))
        rec["preview_frames"][idx]=files

def push_episode_async(ep_dir, repo):
    """Push a single episode folder to HF in background."""
    def do_push():
        try:
            from huggingface_hub import HfApi
            a=HfApi()
            a.create_repo(repo,repo_type="dataset",exist_ok=True)
            # Upload just this episode + meta
            ds_root=ep_dir.parent
            a.upload_folder(folder_path=str(ep_dir),path_in_repo=ep_dir.name,repo_id=repo,repo_type="dataset")
            # Also upload meta.json
            meta_path=ds_root/"meta.json"
            if meta_path.exists():
                a.upload_file(path_or_fileobj=str(meta_path),path_in_repo="meta.json",repo_id=repo,repo_type="dataset")
            socketio.emit("pushed",{"ep":ep_dir.name,"url":f"https://huggingface.co/datasets/{repo}"})
        except Exception as e:
            socketio.emit("push_err",{"e":str(e)})
    threading.Thread(target=do_push,daemon=True).start()

# ═══ ROUTES ═══
@app.route("/")
def index():return render_template_string(HTML)
@app.route("/api/cameras")
def api_cameras():return jsonify({"cams":[{"idx":idx,"name":name} for idx,name in cam_info.items()]})
@app.route("/api/cameras/rename",methods=["POST"])
def api_cam_rename():
    d=request.json or {};idx=int(d.get("idx",-1));name=d.get("name","")
    if idx in cam_info and name:cam_info[idx]=name
    return jsonify({"ok":True,"cams":[{"idx":i,"name":n} for i,n in cam_info.items()]})
@app.route("/api/cameras/swap",methods=["POST"])
def api_cam_swap():
    keys=list(cam_info.keys())
    if len(keys)>=2:
        cam_info[keys[0]],cam_info[keys[1]]=cam_info[keys[1]],cam_info[keys[0]]
    return jsonify({"ok":True,"cams":[{"idx":i,"name":n} for i,n in cam_info.items()]})
@app.route("/video/<int:idx>")
def video(idx):
    if idx not in cam_info:return "Not found",404
    return Response(gen_mjpeg(idx),mimetype='multipart/x-mixed-replace; boundary=frame')
@app.route("/preview/<int:idx>")
def preview_feed(idx):
    if idx not in rec["preview_frames"] or not rec["preview_frames"][idx]:return "No preview",404
    return Response(gen_preview(idx),mimetype='multipart/x-mixed-replace; boundary=frame')
@app.route("/api/snapshot/<int:idx>",methods=["POST"])
def api_snap(idx):
    if idx not in latest_frames:return jsonify({"error":"No camera"})
    os.makedirs("snapshots",exist_ok=True)
    f=f"snapshots/snap_{idx}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    cv2.imwrite(f,latest_frames[idx]);return jsonify({"ok":True,"path":f})
@app.route("/api/ports")
def api_ports():
    try:
        import serial.tools.list_ports;ap=[{"d":p.device,"desc":p.description} for p in serial.tools.list_ports.comports()]
    except:ap=[]
    return jsonify({"ports":ap,"leader":state["leader_port"],"follower":state["follower_port"]})
@app.route("/api/auto_detect",methods=["POST"])
def api_auto_detect():
    found=auto_detect_ports()
    if len(found)>=2:state["leader_port"]=found[0];state["follower_port"]=found[1]
    elif len(found)==1:state["follower_port"]=found[0]
    if found:
        with open(".ports.json","w") as f:json.dump({"leader":state["leader_port"],"follower":state["follower_port"]},f)
    return jsonify({"found":found,"leader":state["leader_port"],"follower":state["follower_port"]})
@app.route("/api/set_ports",methods=["POST"])
def api_set_ports():
    d=request.json;state["leader_port"]=d.get("leader","");state["follower_port"]=d.get("follower","")
    with open(".ports.json","w") as f:json.dump({"leader":state["leader_port"],"follower":state["follower_port"]},f)
    return jsonify({"ok":True})
@app.route("/api/status/<role>")
def api_status(role):
    port=state["follower_port"] if role=="follower" else state["leader_port"]
    return jsonify({"servos":read_servos(port),"temps":state["temp_history"]})
@app.route("/api/teleop/start",methods=["POST"])
def api_teleop_start():
    if state["teleop_running"]:return jsonify({"error":"Already running"})
    if not HAS_LEROBOT:return jsonify({"error":"LeRobot not installed"})
    lp=state["leader_port"];fp=state["follower_port"]
    if not lp or not fp:return jsonify({"error":"Set ports first"})
    state["teleop_running"]=True;state["busy"]=True;state["stop_event"].clear()
    def run():
        dr=0
        try:
            leader=SO101Leader(SO101LeaderConfig(port=lp,id="leader_arm"))
            follower=SO101Follower(SO101FollowerConfig(port=fp,id="follower_arm"))
            leader.connect();follower.connect()
            while not state["stop_event"].is_set():
                try:
                    t0=time.perf_counter();a=leader.get_action();follower.send_action(a);dt=time.perf_counter()-t0
                    socketio.emit("td",{"fps":round(1/max(.001,dt)),"d":dr,"a":{k:round(v,1) for k,v in a.items()}})
                    time.sleep(max(0,.033-dt))
                except ConnectionError:dr+=1
                except:break
            leader.disconnect();follower.disconnect()
        except Exception as e:socketio.emit("te",{"e":str(e)})
        state["teleop_running"]=False;state["busy"]=False;socketio.emit("ts",{})
    threading.Thread(target=run,daemon=True).start();return jsonify({"ok":True})
@app.route("/api/teleop/stop",methods=["POST"])
def api_teleop_stop():state["stop_event"].set();return jsonify({"ok":True})
@app.route("/api/estop",methods=["POST"])
def api_estop():
    state["stop_event"].set()
    for port in [state["leader_port"],state["follower_port"]]:
        if not port or not HAS_SDK:continue
        try:
            with port_lock:
                p=scs.PortHandler(port);p.openPort();p.setBaudRate(1000000);pkt=scs.PacketHandler(0)
                for sid in range(1,7):pkt.write1ByteTxRx(p,sid,40,0)
                p.closePort()
        except:pass
    state["busy"]=False;return jsonify({"ok":True})
@app.route("/api/gesture/<gn>",methods=["POST"])
def api_gesture(gn):
    port=state["follower_port"]
    if not port or not HAS_SDK:return jsonify({"error":"No follower port"})
    if state["busy"]:return jsonify({"error":"Busy"})
    threading.Thread(target=run_gesture,args=(port,gn),daemon=True).start()
    return jsonify({"ok":True})
@app.route("/api/compliant/<action>",methods=["POST"])
def api_compliant(action):
    port=state["follower_port"]
    if not port or not HAS_SDK:return jsonify({"error":"No port"})
    try:
        with port_lock:
            p=scs.PortHandler(port);p.openPort();p.setBaudRate(1000000);pkt=scs.PacketHandler(0)
            if action=="on":
                for sid in range(1,7):pkt.write1ByteTxRx(p,sid,40,0);time.sleep(.05)
            else:
                for sid in range(1,7):
                    pos,_,_=pkt.read2ByteTxRx(p,sid,56);time.sleep(.05);pkt.write2ByteTxRx(p,sid,42,pos);time.sleep(.05)
                for sid in range(1,7):pkt.write1ByteTxRx(p,sid,40,1);time.sleep(.05)
            p.closePort()
        return jsonify({"ok":True})
    except Exception as e:return jsonify({"error":str(e)})
@app.route("/api/calibration_status")
def api_cal():
    h=Path.home()
    fp=h/".cache/huggingface/lerobot/calibration/robots/so101_follower/follower_arm.json"
    lp=h/".cache/huggingface/lerobot/calibration/teleoperators/so101_leader/leader_arm.json"
    return jsonify({"f":fp.exists(),"l":lp.exists(),
        "fc":f"lerobot-calibrate --robot.type=so101_follower --robot.port={state['follower_port'] or '<PORT>'} --robot.id=follower_arm",
        "lc":f"lerobot-calibrate --teleop.type=so101_leader --teleop.port={state['leader_port'] or '<PORT>'} --teleop.id=leader_arm"})
@app.route("/api/reset/<tgt>",methods=["POST"])
def api_reset(tgt):
    ports=[]
    if tgt in ["follower","both"] and state["follower_port"]:ports.append(state["follower_port"])
    if tgt in ["leader","both"] and state["leader_port"]:ports.append(state["leader_port"])
    for port in ports:
        try:
            with port_lock:
                p=scs.PortHandler(port);p.openPort();p.setBaudRate(1000000);pkt=scs.PacketHandler(0)
                for sid in range(1,7):pkt.write1ByteTxRx(p,sid,40,0);time.sleep(.05)
                p.closePort()
        except:pass
    return jsonify({"ok":True})
@app.route("/api/rec/start",methods=["POST"])
def api_rec_start():
    if rec["active"]:return jsonify({"error":"Already recording"})
    if rec["pending"]:return jsonify({"error":"Save or discard first"})
    if not state["follower_port"]:return jsonify({"error":"Set follower port"})
    ds=Path(f"datasets/{rec['ds_name']}");ep_dir=ds/f"episode_{rec['ep_num']:04d}"
    ep_dir.mkdir(parents=True,exist_ok=True);rec["ep_dir"]=ep_dir;rec["active"]=True
    threading.Thread(target=record_worker,daemon=True).start()
    return jsonify({"ok":True,"ep":rec["ep_num"]})
@app.route("/api/rec/stop",methods=["POST"])
def api_rec_stop():
    if not rec["active"]:return jsonify({"error":"Not recording"})
    rec["active"]=False;time.sleep(0.15);rec["pending"]=True
    return jsonify({"ok":True,"frames":rec["count"],"seconds":round(time.time()-rec["t0"],1)})
@app.route("/api/rec/save",methods=["POST"])
def api_rec_save():
    if not rec["pending"]:return jsonify({"error":"Nothing to save"})
    ep_dir=rec["ep_dir"]
    with open(str(ep_dir/"servo_data.json"),"w") as f:
        json.dump({"task":rec["task"],"fps":30,"frames":rec["frames"]},f)
    rec["saved"]+=1;rec["ep_num"]+=1;rec["pending"]=False
    ds=Path(f"datasets/{rec['ds_name']}")
    with open(str(ds/"meta.json"),"w") as f:json.dump({"name":rec["ds_name"],"task":rec["task"],"episodes":rec["saved"],"fps":30},f)
    # Auto-push this episode
    if rec["auto_push"] and rec["repo"]:
        push_episode_async(ep_dir, rec["repo"])
    rec["preview_frames"]={}
    return jsonify({"ok":True,"saved":rec["saved"],"target":rec["target"],"pushing":rec["auto_push"]})
@app.route("/api/rec/discard",methods=["POST"])
def api_rec_discard():
    if not rec["pending"]:return jsonify({"error":"Nothing to discard"})
    shutil.rmtree(rec["ep_dir"],ignore_errors=True);rec["pending"]=False;rec["preview_frames"]={}
    return jsonify({"ok":True})
@app.route("/api/rec/push_all",methods=["POST"])
def api_rec_push_all():
    repo=rec["repo"];ds=Path(f"datasets/{rec['ds_name']}")
    if not ds.exists():return jsonify({"error":"No dataset"})
    def do_push():
        try:
            from huggingface_hub import HfApi
            a=HfApi();a.create_repo(repo,repo_type="dataset",exist_ok=True)
            a.upload_folder(folder_path=str(ds),repo_id=repo,repo_type="dataset")
            socketio.emit("pushed",{"ep":"all","url":f"https://huggingface.co/datasets/{repo}"})
        except Exception as e:socketio.emit("push_err",{"e":str(e)})
    threading.Thread(target=do_push,daemon=True).start();return jsonify({"ok":True})
@app.route("/api/rec/status")
def api_rec_status():return jsonify({"active":rec["active"],"pending":rec["pending"],"saved":rec["saved"],"target":rec["target"],"count":rec["count"],"auto_push":rec["auto_push"]})
@app.route("/api/rec/set_target",methods=["POST"])
def api_rec_set_target():
    d=request.json or {};t=max(1,min(500,int(d.get("target",rec["target"]))));rec["target"]=t
    return jsonify({"ok":True,"target":t})
@app.route("/api/rec/config",methods=["POST"])
def api_rec_config():
    d=request.json or {}
    if "name" in d:rec["ds_name"]=d["name"]
    if "task" in d:rec["task"]=d["task"]
    if "repo" in d:rec["repo"]=d["repo"]
    if "auto_push" in d:rec["auto_push"]=bool(d["auto_push"])
    return jsonify({"ok":True})

# ═══════════════════════════════════════════
HTML=r"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>KIWI</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.4/socket.io.min.js"></script>
<style>
:root{--bg:#E5DDD5;--card:#EDEAE5;--bdr:#D5CEC6;--hov:#F2F0EC;--ink:#2C2520;--ink2:#6B6058;--ink3:#9C9488;--ac:#3D348B;--sg:#4A7C59;--tr:#C4553A;--hn:#C08B30;--r:10px;--r2:7px}
*{margin:0;padding:0;box-sizing:border-box}body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--ink);min-height:100vh;display:flex;flex-direction:column;-webkit-font-smoothing:antialiased}

/* NAV */
nav{height:50px;display:flex;align-items:center;justify-content:space-between;padding:0 20px;background:var(--card);border-bottom:1px solid var(--bdr);position:sticky;top:0;z-index:100;box-shadow:0 1px 3px rgba(0,0,0,.04)}
.brand{display:flex;align-items:center;gap:10px}
.brand-dot{width:30px;height:30px;border-radius:8px;background:var(--ac);display:grid;place-items:center}
.brand-dot svg{width:17px;height:17px;fill:none;stroke:#fff;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.brand h1{font-size:15px;font-weight:700;color:var(--ink)}
.nav-r{display:flex;align-items:center;gap:8px}
.nav-r label{font-size:8px;color:var(--ink3);font-weight:600}
.nav-r input{width:95px;height:26px;background:var(--bg);border:1px solid var(--bdr);border-radius:5px;padding:0 7px;font-family:'JetBrains Mono',monospace;font-size:9px;outline:none;color:var(--ink)}.nav-r input:focus{border-color:var(--ac)}
.nb{height:26px;padding:0 10px;border:1px solid var(--bdr);border-radius:5px;background:var(--card);font-size:8px;font-weight:600;cursor:pointer;color:var(--ink2);font-family:inherit}.nb:hover{border-color:var(--ac);color:var(--ac)}
.dot{width:7px;height:7px;border-radius:50%;display:inline-block;margin-left:2px}.dot.on{background:var(--sg);box-shadow:0 0 4px rgba(61,122,74,.4)}.dot.off{background:var(--bdr)}
.estop{background:var(--tr);color:#fff;border:none;height:26px;padding:0 12px;border-radius:5px;font-size:9px;font-weight:700;cursor:pointer;letter-spacing:.3px}.estop:hover{filter:brightness(1.1)}

/* TABS */
.tabs{display:flex;background:var(--card);border-bottom:1px solid var(--bdr);padding:0 20px}
.tab{padding:11px 22px;font-size:12px;font-weight:600;color:var(--ink3);cursor:pointer;border-bottom:2.5px solid transparent;transition:.15s}.tab:hover{color:var(--ink)}.tab.active{color:var(--ac);border-bottom-color:var(--ac)}
.tc{display:none;flex:1;overflow:auto}.tc.active{display:block}

/* SHARED */
.card{background:var(--card);border:1px solid var(--bdr);border-radius:var(--r);padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.03)}
.card h3{font-size:11px;font-weight:700;margin-bottom:10px;color:var(--ink);display:flex;justify-content:space-between;align-items:center}
.card h3 .badge{font-size:8px;font-weight:600;padding:2px 8px;border-radius:12px}
.card h3 .badge.on{background:rgba(61,122,74,.1);color:var(--sg)}.card h3 .badge.off{background:rgba(192,66,43,.08);color:var(--tr)}

/* CAMERAS */
.cam-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:8px}
.cam{position:relative;background:#0a0a0a;border-radius:var(--r);overflow:hidden;aspect-ratio:4/3}
.cam img{width:100%;height:100%;object-fit:contain;display:block}
.cam-tag{position:absolute;top:7px;left:7px;background:rgba(0,0,0,.65);color:#fff;font-size:8px;font-weight:600;padding:3px 10px;border-radius:14px;backdrop-filter:blur(4px)}
.cam-badge{position:absolute;top:7px;right:7px;font-size:7px;font-weight:700;padding:2px 8px;border-radius:14px}
.cam-badge.live{background:rgba(61,122,74,.85);color:#fff}.cam-badge.rec{background:rgba(192,66,43,.9);color:#fff;animation:pulse 1s ease infinite}
.cam-badge.preview{background:rgba(74,61,143,.85);color:#fff;animation:pulse 1.5s ease infinite}
.cam-snap{position:absolute;bottom:7px;right:7px;width:28px;height:28px;border-radius:50%;border:none;background:rgba(255,255,255,.12);color:#fff;cursor:pointer;display:grid;place-items:center;backdrop-filter:blur(4px)}
.cam-snap:hover{background:rgba(74,61,143,.7)}
.cam-snap svg{width:12px;height:12px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round}
.cam-swap{position:absolute;bottom:7px;left:7px;height:24px;padding:0 8px;border-radius:14px;border:none;background:rgba(255,255,255,.12);color:#fff;cursor:pointer;font-size:7px;font-weight:600;font-family:inherit;backdrop-filter:blur(4px)}.cam-swap:hover{background:rgba(74,61,143,.7)}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}

/* ARMS */
.j{display:flex;align-items:center;gap:5px;padding:3px 0}
.j .jn{font-size:9px;color:var(--ink3);width:40px;font-weight:500}
.j .jbar{flex:1;height:4px;background:var(--bg);border-radius:2px;overflow:hidden}
.j .jfill{height:100%;border-radius:2px;background:var(--ac);transition:width .3s}
.j .jv{font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:600;color:var(--ink2);width:30px;text-align:right}
.j .jt{font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:600;width:22px;text-align:right}
.jt.ok{color:var(--sg)}.jt.wn{color:var(--hn)}.jt.ht{color:var(--tr)}

/* GESTURES */
.gg{display:grid;grid-template-columns:repeat(7,1fr);gap:8px}
.gi{aspect-ratio:1;width:auto;height:auto;background:var(--bg);border:1px solid var(--bdr);border-radius:var(--r2);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;cursor:pointer;transition:.15s}
.gi:hover{border-color:var(--ac);background:var(--hov);transform:translateY(-1px)}
.gi svg{width:28px;height:28px;stroke:var(--ink3);fill:none;stroke-width:1.5;stroke-linecap:round;stroke-linejoin:round;transition:.15s}.gi:hover svg{stroke:var(--ac)}
.gi span{font-size:9px;font-weight:600;color:var(--ink3)}.gi:hover span{color:var(--ac)}

/* TELEOP */
.tele{display:flex;align-items:center;gap:12px}
.tbtn{width:58px;height:58px;border-radius:50%;border:2.5px solid var(--bdr);background:var(--bg);display:grid;place-items:center;cursor:pointer;transition:.2s;flex-shrink:0}
.tbtn:hover{border-color:var(--ac);box-shadow:0 0 12px rgba(74,61,143,.12)}.tbtn.on{border-color:var(--tr);background:rgba(192,66,43,.04)}
.tbtn span{font-size:10px;font-weight:700;color:var(--ac)}.tbtn.on span{color:var(--tr)}
.tnum{font-family:'JetBrains Mono',monospace;font-size:18px;font-weight:700;color:var(--ac)}.tlab{font-size:7px;color:var(--ink3);text-transform:uppercase;letter-spacing:1px}

/* BUTTONS */
.btn{display:inline-flex;align-items:center;justify-content:center;padding:7px 14px;border:none;border-radius:6px;font-size:10px;font-weight:600;cursor:pointer;font-family:inherit;transition:.15s}
.btn:hover{transform:translateY(-1px)}
.ba{background:var(--ac);color:#fff}.bs{background:var(--sg);color:#fff}.bt{background:var(--tr);color:#fff}.bh{background:var(--hn);color:#fff}
.bg{background:var(--bg);color:var(--ink2);border:1px solid var(--bdr)}.bg:hover{background:var(--hov)}
.brow{display:flex;gap:6px;flex-wrap:wrap}

/* CALIBRATION */
.cmd{background:var(--bg);border:1px solid var(--bdr);border-radius:5px;padding:5px 8px;font-family:'JetBrains Mono',monospace;font-size:8px;color:var(--ink2);cursor:pointer;margin-top:3px;word-break:break-all}.cmd:hover{border-color:var(--ac)}.cmd:active{background:var(--ac);color:#fff}
.cok{color:var(--sg);font-size:9px;font-weight:600}.cno{color:var(--tr);font-size:9px;font-weight:600}

/* LAYOUTS */
.cc{display:grid;grid-template-columns:1fr 290px;gap:12px;padding:14px 20px 24px;max-width:1400px;width:100%;margin:0 auto}
@media(max-width:960px){.cc{grid-template-columns:1fr}}
.cc-l,.cc-r{display:flex;flex-direction:column;gap:12px}
.arms{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media(max-width:700px){.arms{grid-template-columns:1fr}}

/* RECORDER */
.rl{display:grid;grid-template-columns:1fr 310px;max-width:1400px;width:100%;margin:0 auto;flex:1}
@media(max-width:960px){.rl{grid-template-columns:1fr}}
.rl-l{background:#0a0a0a;display:flex;flex-direction:column;padding:8px}
.rl-r{background:var(--card);border-left:1px solid var(--bdr);padding:16px;overflow-y:auto}
@media(max-width:960px){.rl-r{border-left:none;border-top:1px solid var(--bdr)}}
.rec-bar{height:40px;background:#141414;display:flex;align-items:center;justify-content:center;gap:12px;border-radius:0 0 var(--r) var(--r);margin-top:4px}
.rdot{width:10px;height:10px;border-radius:50%;background:#333;flex-shrink:0}.rdot.on{background:#e53935;animation:pulse 1s ease infinite}.rdot.pending{background:var(--ac);animation:pulse 1.5s ease infinite}
.rtxt{font-family:'JetBrains Mono',monospace;font-size:12px;color:#777;font-weight:600}.rtxt.on{color:#e53935}.rtxt.pending{color:var(--ac)}

.counter{text-align:center;padding:14px;background:var(--bg);border-radius:var(--r);border:1px solid var(--bdr);margin-bottom:12px}
.counter .num{font-family:'JetBrains Mono',monospace;font-size:30px;font-weight:700;color:var(--ac)}
.counter .label{font-size:8px;color:var(--ink3);text-transform:uppercase;letter-spacing:1px;margin-top:2px}
.pbar{height:5px;background:var(--bdr);border-radius:3px;overflow:hidden;margin-top:6px}.pbar-fill{height:100%;background:var(--ac);border-radius:3px;transition:width .3s}
.trow{display:flex;align-items:center;justify-content:center;gap:6px;margin-top:8px}
.trow span{font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:600;color:var(--ink2);min-width:36px;text-align:center}
.pm{width:28px;height:28px;border-radius:50%;border:1.5px solid var(--bdr);background:var(--card);font-size:14px;font-weight:700;color:var(--ink2);cursor:pointer;display:grid;place-items:center;font-family:'JetBrains Mono',monospace}.pm:hover{border-color:var(--ac);color:var(--ac)}

.big{width:100%;height:50px;border:none;border-radius:var(--r);font-size:14px;font-weight:700;cursor:pointer;font-family:inherit;transition:.15s;margin-bottom:10px;letter-spacing:.3px}
.big:hover{filter:brightness(1.05)}.big.start{background:var(--sg);color:#fff}.big.stop{background:var(--tr);color:#fff}.big.off{background:var(--bdr);color:var(--ink3);pointer-events:none}
.srow{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px}
.sv{height:44px;border:none;border-radius:var(--r2);font-size:12px;font-weight:700;cursor:pointer;font-family:inherit;transition:.15s}.sv.yes{background:var(--sg);color:#fff}.sv.no{background:var(--tr);color:#fff}
.sv:hover{filter:brightness(1.1)}.sv.off{background:var(--bdr);color:var(--ink3);pointer-events:none}

.fi{width:100%;height:30px;background:var(--bg);border:1px solid var(--bdr);border-radius:5px;padding:0 9px;font-family:'JetBrains Mono',monospace;font-size:9px;outline:none;margin-bottom:6px;color:var(--ink)}.fi:focus{border-color:var(--ac)}
.fi-label{font-size:8px;font-weight:600;color:var(--ink3);margin-bottom:3px}
.push{width:100%;height:36px;border:none;border-radius:var(--r2);background:var(--ac);color:#fff;font-size:10px;font-weight:700;cursor:pointer;font-family:inherit;margin-top:8px}.push:hover{filter:brightness(1.1)}
.hint{font-size:8px;color:var(--ink3);text-align:center;margin-top:5px}
.toggle-row{display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-top:1px solid var(--bdr);margin-top:8px}
.toggle-row span{font-size:9px;font-weight:600;color:var(--ink2)}
.toggle{width:36px;height:20px;border-radius:10px;background:var(--bdr);cursor:pointer;position:relative;transition:.2s}
.toggle.on{background:var(--sg)}
.toggle::after{content:'';width:16px;height:16px;border-radius:50%;background:#fff;position:absolute;top:2px;left:2px;transition:.2s;box-shadow:0 1px 2px rgba(0,0,0,.15)}
.toggle.on::after{left:18px}

.toast{position:fixed;bottom:16px;left:50%;transform:translateX(-50%) translateY(40px);padding:9px 22px;border-radius:8px;font-size:11px;font-weight:500;z-index:1000;opacity:0;transition:.3s;pointer-events:none;background:var(--ink);color:#fff;box-shadow:0 4px 12px rgba(0,0,0,.15)}.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
::selection{background:rgba(74,61,143,.12)}
</style></head><body>

<nav>
<div class="brand"><div class="brand-dot"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg></div><h1>KIWI Control Center</h1></div>
<div class="nav-r"><label>Leader</label><input id="lp"><label>Follower</label><input id="fp"><button class="nb" onclick="autoD()">Auto</button><button class="nb" onclick="saveP()">Save</button>
<span style="font-size:8px;color:var(--ink3)">L<span class="dot" id="ld"></span> F<span class="dot" id="fd"></span></span><button class="estop" onclick="estop()">E-STOP</button></div>
</nav>
<div class="tabs"><div class="tab active" onclick="stab('cc')">Dashboard</div><div class="tab" onclick="stab('rec')">Recorder</div></div>

<!-- ═══ DASHBOARD TAB ═══ -->
<div class="tc active" id="t-cc"><div class="cc">
<div class="cc-l">
<div class="card" style="padding:10px"><div class="cam-grid" id="cc-cams">Loading cameras...</div></div>
<div class="arms">
<div class="card"><h3>Follower <span class="badge off" id="fb">offline</span></h3><div id="fs"></div></div>
<div class="card"><h3>Leader <span class="badge off" id="lb">offline</span></h3><div id="ls"></div></div>
</div>
<div class="card"><h3>Gestures</h3><div class="gg">
<div class="gi" style="background:#EDE7F6;border-color:#B39DDB" onclick="G('wave')"><svg viewBox="0 0 24 24"><path d="M18 11V6a2 2 0 0 0-2-2 2 2 0 0 0-2 2"/><path d="M14 10V4a2 2 0 0 0-2-2 2 2 0 0 0-2 2v2"/><path d="M10 10.5V6a2 2 0 0 0-2-2 2 2 0 0 0-2 2v8"/><path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15"/></svg><span>Wave</span></div>
<div class="gi" style="background:#E8F5E9;border-color:#A5D6A7" onclick="G('thumbsup')"><svg viewBox="0 0 24 24"><path d="M7 10v12"/><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z"/></svg><span>OK</span></div>
<div class="gi" style="background:#FFF3E0;border-color:#FFCC80" onclick="G('point')"><svg viewBox="0 0 24 24"><path d="m9 11-6 6v3h9l3-3"/><path d="m22 12-4.6 4.6a2 2 0 0 1-2.8 0l-5.2-5.2a2 2 0 0 1 0-2.8L14 4"/></svg><span>Point</span></div>
<div class="gi" style="background:#E3F2FD;border-color:#90CAF9" onclick="G('nod')"><svg viewBox="0 0 24 24"><polyline points="18 15 12 9 6 15"/></svg><span>Nod</span></div>
<div class="gi" style="background:#FCE4EC;border-color:#F48FB1" onclick="G('shake')"><svg viewBox="0 0 24 24"><path d="M2 12h4"/><path d="M18 12h4"/><path d="m15 5-3 3-3-3"/><path d="m15 19-3-3-3 3"/></svg><span>Shake</span></div>
<div class="gi" style="background:#FFF8E1;border-color:#FFD54F" onclick="G('dance')"><svg viewBox="0 0 24 24"><circle cx="12" cy="4" r="2"/><path d="M4.05 11.55 8 13.54a2 2 0 0 0 2.04-.07L12 12l1.93 1.47a2 2 0 0 0 2.04.07l3.98-1.99"/></svg><span>Dance</span></div>
<div class="gi" style="background:#EFEBE9;border-color:#BCAAA4" onclick="G('home')"><svg viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg><span>Home</span></div>
</div></div>
</div>
<div class="cc-r">
<div class="card"><h3>Teleoperation</h3><div class="tele"><div class="tbtn" id="tr" onclick="toggleT()"><span id="tl">START</span></div><div style="flex:1"><div style="display:flex;gap:16px"><div><div class="tnum" id="tf">--</div><div class="tlab">FPS</div></div><div><div class="tnum" id="td2">0</div><div class="tlab">Drops</div></div></div></div></div></div>
<div class="card"><h3>Controls</h3><div class="brow"><button class="btn bs" onclick="C('on')">Free Move</button><button class="btn bg" onclick="C('off')">Lock</button><button class="btn bg" onclick="G('home')">Home</button><button class="btn bh" onclick="if(confirm('Reset?'))api('/api/reset/both','POST').then(()=>toast('Reset'))">Reset</button></div></div>
<div class="card"><h3>Calibration</h3><div id="cal"></div></div>
</div>
</div></div>

<!-- ═══ RECORDER TAB ═══ -->
<div class="tc" id="t-rec"><div class="rl">
<div class="rl-l">
<div class="cam-grid" id="rec-cams" style="flex:1">Loading cameras...</div>
<div class="rec-bar"><div class="rdot" id="rdot"></div><div class="rtxt" id="rtxt">IDLE — teleop active, move leader arm</div></div>
</div>
<div class="rl-r">
<div class="counter"><div class="num" id="epc">0</div><div class="label">Episodes Saved</div><div class="pbar"><div class="pbar-fill" id="pbar" style="width:0%"></div></div>
<div class="trow"><span style="font-size:8px;color:var(--ink3)">Target:</span><button class="pm" onclick="adjT(-10)">-10</button><button class="pm" onclick="adjT(-1)">-</button><span id="tgt">50</span><button class="pm" onclick="adjT(1)">+</button><button class="pm" onclick="adjT(10)">+10</button></div></div>
<button class="big start" id="rbtn" onclick="toggleR()">START RECORDING</button>
<div class="srow"><button class="sv yes off" id="sbtn" onclick="saveR()">SAVE (y)</button><button class="sv no off" id="dbtn" onclick="discR()">DISCARD (n)</button></div>
<div class="fi-label">Dataset Name</div><input class="fi" id="dn" value="so101_pick_place" onchange="recCfg()">
<div class="fi-label">Task</div><input class="fi" id="dtask" value="Pick object and place in box" onchange="recCfg()">
<div class="fi-label">HuggingFace Repo</div><input class="fi" id="dr" value="G3nadh/so101_pick_place" onchange="recCfg()">
<div class="toggle-row"><span>Auto-push to HF on save</span><div class="toggle on" id="ap-toggle" onclick="toggleAP()"></div></div>
<button class="push" onclick="pushAll()">Push All to HuggingFace</button>
<div class="hint">Keyboard: Enter = start/stop, y = save, n = discard</div>
</div>
</div></div>

<div class="toast" id="toast"></div>
<script>
const S=io();let TO=false,isR=false,isP=false,curTab='cc',camList=[],autoPush=true;
const $=id=>document.getElementById(id);
const api=(u,m,b)=>{const o={method:m||'GET',headers:{'Content-Type':'application/json'}};if(b)o.body=JSON.stringify(b);return fetch(u,o).then(r=>r.json())};
const toast=m=>{const t=$('toast');t.textContent=m;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2500)};
function stab(id){curTab=id;document.querySelectorAll('.tab').forEach((t,i)=>t.classList.toggle('active',i===(id==='cc'?0:1)));
document.querySelectorAll('.tc').forEach(t=>t.classList.remove('active'));$('t-'+id).classList.add('active')}

/* CAMERAS */
function loadCams(){api('/api/cameras').then(d=>{camList=d.cams;
if(!camList.length){$('cc-cams').innerHTML=$('rec-cams').innerHTML='<div style="color:#999;text-align:center;padding:30px">No cameras detected</div>';return}
$('cc-cams').innerHTML=camList.map(c=>'<div class="cam"><img src="/video/'+c.idx+'"><div class="cam-tag">'+c.name+'</div><div class="cam-badge live">LIVE</div><button class="cam-snap" onclick="snap('+c.idx+')"><svg viewBox="0 0 24 24"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg></button></div>').join('');
$('rec-cams').innerHTML=camList.map(c=>'<div class="cam"><img id="rcam'+c.idx+'" src="/video/'+c.idx+'"><div class="cam-tag">'+c.name+'</div><div class="cam-badge live" id="cb'+c.idx+'">LIVE</div>'+(camList.length>1?'<button class="cam-swap" onclick="swapCams()">Swap</button>':'')+'</div>').join('')})}
function snap(i){api('/api/snapshot/'+i,'POST').then(d=>toast(d.error||'Snapshot saved'))}
function swapCams(){api('/api/cameras/swap','POST').then(()=>{loadCams();toast('Cameras swapped')})}
function setRecLive(){camList.forEach(c=>{const el=$('rcam'+c.idx);if(el)el.src='/video/'+c.idx;const b=$('cb'+c.idx);if(b){b.textContent='LIVE';b.className='cam-badge live'}})}
function setRecPreview(){camList.forEach(c=>{const el=$('rcam'+c.idx);if(el)el.src='/preview/'+c.idx+'?t='+Date.now();const b=$('cb'+c.idx);if(b){b.textContent='PREVIEW';b.className='cam-badge preview'}})}
function setRecRec(){camList.forEach(c=>{const b=$('cb'+c.idx);if(b){b.textContent='REC';b.className='cam-badge rec'}})}

/* ARMS */
function renderA(id,bid,data){const b=$(bid);if(!data){b.textContent='offline';b.className='badge off';$(id).innerHTML='';return}
b.textContent='online';b.className='badge on';$(id).innerHTML=data.map(s=>{const tc=s.temp>=50?'ht':s.temp>=40?'wn':'ok';
return '<div class="j"><span class="jn">'+s.name.split('_').pop()+'</span><div class="jbar"><div class="jfill" style="width:'+s.pct+'%"></div></div><span class="jv">'+s.position+'</span><span class="jt '+tc+'">'+s.temp+'°</span></div>'}).join('')}
function refresh(){api('/api/status/follower').then(d=>{renderA('fs','fb',d.servos);$('fd').className='dot '+(d.servos?'on':'off')});
api('/api/status/leader').then(d=>{renderA('ls','lb',d.servos);$('ld').className='dot '+(d.servos?'on':'off')})}
function saveP(){api('/api/set_ports','POST',{leader:$('lp').value,follower:$('fp').value}).then(()=>{toast('Ports saved');refresh();checkCal()})}
function autoD(){toast('Scanning...');api('/api/auto_detect','POST').then(d=>{if(!d.found.length){toast('No arms found');return}$('lp').value=d.leader||'';$('fp').value=d.follower||'';toast(d.found.length+' arm(s) found');refresh();checkCal()})}
function G(n){api('/api/gesture/'+n,'POST').then(d=>toast(d.error||n))}
function C(a){api('/api/compliant/'+a,'POST').then(d=>toast(d.error||(a==='on'?'Free move':'Locked')))}
function estop(){api('/api/estop','POST');toast('Emergency stop!')}
function toggleT(){if(!TO){api('/api/teleop/start','POST').then(d=>{if(d.error){toast(d.error);return}TO=true;$('tr').classList.add('on');$('tl').textContent='STOP'})}else{api('/api/teleop/stop','POST')}}
S.on('td',d=>{$('tf').textContent=d.fps;$('td2').textContent=d.d});
S.on('ts',()=>{TO=false;$('tr').classList.remove('on');$('tl').textContent='START'});
S.on('te',d=>toast(d.e));S.on('err',d=>toast(d.e));
function checkCal(){api('/api/calibration_status').then(d=>{$('cal').innerHTML=
'<div style="margin-bottom:4px"><span class="'+(d.f?'cok':'cno')+'">'+(d.f?'Follower calibrated':'Follower not calibrated')+'</span><div class="cmd" onclick="navigator.clipboard.writeText(this.textContent);toast(\'Copied\')">'+d.fc+'</div></div>'+
'<div><span class="'+(d.l?'cok':'cno')+'">'+(d.l?'Leader calibrated':'Leader not calibrated')+'</span><div class="cmd" onclick="navigator.clipboard.writeText(this.textContent);toast(\'Copied\')">'+d.lc+'</div></div>'})}

/* RECORDER */
function updR(){api('/api/rec/status').then(d=>{$('epc').textContent=d.saved;$('tgt').textContent=d.target;const p=d.target>0?Math.min(100,Math.round(d.saved/d.target*100)):0;$('pbar').style.width=p+'%'})}
function adjT(d){let t=parseInt($('tgt').textContent)+d;if(t<1)t=1;if(t>500)t=500;$('tgt').textContent=t;api('/api/rec/set_target','POST',{target:t})}
function toggleAP(){autoPush=!autoPush;$('ap-toggle').className='toggle'+(autoPush?' on':'');api('/api/rec/config','POST',{auto_push:autoPush})}
function toggleR(){
if(isP){toast('Save or discard first');return}
if(!isR){api('/api/rec/start','POST').then(d=>{if(d.error){toast(d.error);return}isR=true;$('rbtn').textContent='STOP RECORDING';$('rbtn').className='big stop';$('rdot').className='rdot on';$('rtxt').className='rtxt on';$('sbtn').className='sv yes off';$('dbtn').className='sv no off';setRecRec()})}
else{api('/api/rec/stop','POST').then(d=>{if(d.error){toast(d.error);return}isR=false;isP=true;$('rbtn').textContent='REVIEW EPISODE';$('rbtn').className='big off';$('rdot').className='rdot pending';$('rtxt').textContent='PREVIEW — '+d.frames+' frames, '+d.seconds+'s';$('rtxt').className='rtxt pending';$('sbtn').className='sv yes';$('dbtn').className='sv no';setTimeout(()=>setRecPreview(),300)})}}
function saveR(){api('/api/rec/save','POST').then(d=>{if(d.error){toast(d.error);return}isP=false;$('rbtn').textContent='START RECORDING';$('rbtn').className='big start';$('rdot').className='rdot';$('rtxt').textContent=d.pushing?'SAVED & PUSHING to HF...':'SAVED — ready';$('rtxt').className='rtxt';$('sbtn').className='sv yes off';$('dbtn').className='sv no off';setRecLive();toast('Episode saved! ('+d.saved+'/'+d.target+')');updR();if(d.saved>=d.target)toast('Target reached!')})}
function discR(){api('/api/rec/discard','POST').then(d=>{if(d.error){toast(d.error);return}isP=false;$('rbtn').textContent='START RECORDING';$('rbtn').className='big start';$('rdot').className='rdot';$('rtxt').textContent='DISCARDED — try again';$('rtxt').className='rtxt';$('sbtn').className='sv yes off';$('dbtn').className='sv no off';setRecLive();toast('Episode discarded')})}
function recCfg(){api('/api/rec/config','POST',{name:$('dn').value,task:$('dtask').value,repo:$('dr').value})}
function pushAll(){toast('Pushing all to HuggingFace...');api('/api/rec/push_all','POST')}
S.on('rec_tick',d=>{$('rtxt').textContent='REC  '+d.f+' frames · '+d.t+'s'});
S.on('pushed',d=>toast('Pushed '+d.ep+'! '+d.url));
S.on('push_err',d=>toast('Push failed: '+d.e));
document.addEventListener('keydown',e=>{if(e.target.tagName==='INPUT')return;if(curTab==='rec'){if(e.key==='Enter'){e.preventDefault();toggleR()}if(e.key==='y'&&isP){e.preventDefault();saveR()}if(e.key==='n'&&isP){e.preventDefault();discR()}}});
api('/api/ports').then(d=>{$('lp').value=d.leader;$('fp').value=d.follower});
loadCams();refresh();checkCal();updR();setInterval(()=>{if(!TO&&curTab==='cc')refresh()},3000);
</script></body></html>"""

if __name__=="__main__":
    print("\n  KIWI Control Center — Final")
    print("  ────────────────────────────")
    init_cameras()
    print(f"  Cameras: {len(cam_info)} detected")
    print(f"  SDK: {'yes' if HAS_SDK else 'NO'}")
    print(f"  LeRobot: {'yes' if HAS_LEROBOT else 'NO'}")
    print(f"\n  http://localhost:5000\n")
    socketio.run(app,host="0.0.0.0",port=5000,debug=False,allow_unsafe_werkzeug=True)
