<h1 align="center">SO-ARM101 Servo Motor Configuring</h1>

The servo calibration and initialization process for SO-ARM101 is the same as that of SO-ARM100 in terms of both method and code. However, please note that the gear ratios for the first three joints of the SO-ARM101 Leader Arm differ from those of SO-ARM100, so it’s important to distinguish and calibrate them carefully.

To configure the motors designate one bus servo adapter and 6 motors for your leader arm, and similarly the other bus servo adapter and 6 motors for the follower arm. It's convenient to label them and write on each motor if it's for the follower F or for the leader L and it's ID from 1 to 6. We use F1–F6 to represent joints 1 to 6 of the Follower Arm, and L1–L6 to represent joints 1 to 6 of the Leader Arm. The corresponding servo model, joint assignments, and gear ratio details are as follows:

<table align="center">
    <thead>
        <th align="center" style="width:60%">Servo Model</th>
        <th align="center" style="width:20%">Gear Ratio</th>
        <th align="center" style="width:20%">Corresponding Joints</th>
    </thead>
    <tbody>
        <tr>
            <td>
                ST-3215-C044(7.4V)
            </td>
            <td>
                1:191
            </td>
            <td>
                L1
            </td>
        </tr>
        <tr>
            <td>
                ST-3215-C001(7.4V)
            </td>
            <td>
                1:345
            </td>
            <td>
                L2
            </td>
        </tr>
        <tr>
            <td>
                ST-3215-C044(7.4V)
            </td>
            <td>
                1:191
            </td>
            <td>
                L3
            </td>
        </tr>
        <tr>
            <td>
                ST-3215-C046(7.4V)
            </td>
            <td>
                1:147
            </td>
            <td>
                L4–L6
            </td>
        </tr>
        <tr>
            <td>
                ST-3215-C001(7.4V) / C018(12V) / C047(12V)
            </td>
            <td>
                1:345	
            </td>
            <td>
                F1–F6
            </td>
        </tr>
    </tbody>
</table>

<div style="
  border-radius:6px;
  border:1px solid #5b0000;
  background:#3b0000;
  padding:12px 16px;
  color:#ffffff;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  margin:16px 0;
">
  <div style="font-weight:700; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:6px; display:flex; align-items:center;">
    <span style="font-size:18px; margin-right:8px;">🔥</span>
    <span>Important</span>
  </div>
  <div style="font-size:14px; line-height:1.5;">
    You now should plug the 5V or 12V power supply to the motor bus. 5V for the STS3215 7.4V motors and 12V for the STS3215 12V motors.
    Note that the leader arm always uses the 7.4V motors, so watch out that you plug in the right power supply if you have 12V and 7.4V motors,
    otherwise you might burn your motors! Now, connect the motor bus to your computer via USB. Note that the USB doesn't provide any power,
    and both the power supply and USB have to be plugged in.
  </div>
</div>

<img src="../assets\images\configure\image.png">


<h1 align="center">Step-by-Step Assembly Instructions</h1>

The follower arm uses 6x STS3215 motors with 1/345 gearing. The leader, however, uses three differently geared motors to make sure it can both sustain its own weight and it can be moved without requiring much force. Which motor is needed for which joint is shown in the table below.

<div align="center">
  <div style="
    margin:16px auto;
    display:inline-block;
    border-radius:10px;
    overflow:hidden;
    background:#111;
    border:1px solid #202632;
    font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
    font-size:14px;
    color:#e5e7eb;
  ">
    <table style="border-collapse:collapse; min-width:260px;">
      <thead>
        <tr style="background:#111;">
          <th style="padding:10px 14px; border-bottom:1px solid #202632; text-align:left; font-weight:600;">
            Leader-Arm Axis
          </th>
          <th style="padding:10px 14px; border-bottom:1px solid #202632; text-align:left; font-weight:600;">
            Motor
          </th>
          <th style="padding:10px 14px; border-bottom:1px solid #202632; text-align:left; font-weight:600;">
            Gear Ratio
          </th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td style="padding:8px 14px; border-top:1px solid #202632;">Base / Shoulder Pan</td>
          <td style="padding:8px 14px; border-top:1px solid #202632;">1</td>
          <td style="padding:8px 14px; border-top:1px solid #202632;">1 / 191</td>
        </tr>
        <tr>
          <td style="padding:8px 14px; border-top:1px solid #202632;">Shoulder Lift</td>
          <td style="padding:8px 14px; border-top:1px solid #202632;">2</td>
          <td style="padding:8px 14px; border-top:1px solid #202632;">1 / 345</td>
        </tr>
        <tr>
          <td style="padding:8px 14px; border-top:1px solid #202632;">Elbow Flex</td>
          <td style="padding:8px 14px; border-top:1px solid #202632;">3</td>
          <td style="padding:8px 14px; border-top:1px solid #202632;">1 / 191</td>
        </tr>
        <tr>
          <td style="padding:8px 14px; border-top:1px solid #202632;">Wrist Flex</td>
          <td style="padding:8px 14px; border-top:1px solid #202632;">4</td>
          <td style="padding:8px 14px; border-top:1px solid #202632;">1 / 147</td>
        </tr>
        <tr>
          <td style="padding:8px 14px; border-top:1px solid #202632;">Wrist Roll</td>
          <td style="padding:8px 14px; border-top:1px solid #202632;">5</td>
          <td style="padding:8px 14px; border-top:1px solid #202632;">1 / 147</td>
        </tr>
        <tr>
          <td style="padding:8px 14px; border-top:1px solid #202632;">Gripper</td>
          <td style="padding:8px 14px; border-top:1px solid #202632;">6</td>
          <td style="padding:8px 14px; border-top:1px solid #202632;">1 / 147</td>
        </tr>
      </tbody>
    </table>
  </div>
</div>

<br>

<h2>Configure the motors</h2>
<h3>1. Find the USB ports associated with each arm</h3>
To find the port for each bus servo adapter, connect MotorBus to your computer via USB and power. Run the following script and disconnect the MotorBus when prompted:

<div style="
  margin:12px 0;
  background:#202632;
  border-radius:8px;
  border:1px solid #111;
  padding:8px 12px;
  font-family:SFMono-Regular,Menlo,Monaco,Consolas,'Liberation Mono','Courier New',monospace;
  font-size:13px;
  color:#e5e7eb;
  display:flex;
  align-items:center;
  justify-content:space-between;
">
  <span>lerobot-find-port</span>
</div>

<h3><code>Linux</code></h3>
On Linux, you might need to give access to the USB ports by running:
<div style="
  margin:12px 0;
  background:#1f2933;              /* gray-ish background */
  border-radius:8px;
  border:1px solid #374151;
  padding:10px 14px;
  font-family:SFMono-Regular,Menlo,Monaco,Consolas,'Liberation Mono','Courier New',monospace;
  font-size:14px;
  color:#e5e7eb;
  white-space:pre;
">
sudo <span style="color:#a3e635;">chmod</span> 666 /dev/ttyACM0
sudo <span style="color:#a3e635;">chmod</span> 666 /dev/ttyACM1
</div>

```Example output:```

```
Finding all available ports for the MotorBus.
['/dev/ttyACM0', '/dev/ttyACM1']
Remove the usb cable from your MotorsBus and press Enter when done.

[...Disconnect corresponding leader or follower arm and press Enter...]

The port of this MotorsBus is /dev/ttyACM1
Reconnect the USB cable.
```
Where the found port is: /dev/ttyACM1 corresponding to your leader or follower arm.

<h3>2. Set the motors ids and baudrates</h3>
<p>
Each motor is identified by a unique id on the bus. When brand new, motors usually come with a default id of 1. For the communication to work properly between the motors and the controller, we first need to set a unique, different id to each motor. Additionally, the speed at which data is transmitted on the bus is determined by the baudrate. In order to talk to each other, the controller and all the motors need to be configured with the same baudrate.<br>

To that end, we first need to connect to each motor individually with the controller in order to set these. Since we will write these parameters in the non-volatile section of the motors’ internal memory (EEPROM), we’ll only need to do this once.

If you are repurposing motors from another robot, you will probably also need to perform this step as the ids and baudrate likely won’t match.

The video below shows the sequence of steps for setting the motor ids.
</p>

<h3 align="center"><code>Setup motors video</code></h3>
<p align="center">
<video 
  src="..\assets\images\configure\setup_motors_so101_2.mp4"
  controls
  width="640"
  poster="assets/thumbnails/so101_demo.png">
  Your browser does not support the video tag.
</video>
</p>

<h2>Follower</h2>
Connect the usb cable from your computer and the power supply to the follower arm’s controller board. Then, run the following command or run the API example with the port you got from the previous step. You’ll also need to give your leader arm a name with the id parameter.
<br>
<br>

```command```

```
    lerobot-setup-motors \
    --robot.type=so101_follower \
    --robot.port=/dev/tty.usbmodem585A0076841  # <- paste here the port found at previous step
```

You should see the following instruction

```
    Connect the controller board to the 'gripper' motor only and press enter.
```

As instructed, plug the gripper’s motor. Make sure it’s the only motor connected to the board, and that the motor itself is not yet daisy-chained to any other motor. As you press [Enter], the script will automatically set the id and baudrate for that motor.

> Troubleshooting
> If you get an error at that point, check your cables and make sure they are plugged in properly:
> - Power supply
> - USB cable between your computer and the controller board
> - The 3-pin cable from the controller board to the motor<br><br>
> If you are using a Waveshare controller board, make sure that the two jumpers are set on the B channel (USB).<br>

Followed by the next instruction:

```
    Connect the controller board to the 'wrist_roll' motor only and press enter.
```

You can disconnect the 3-pin cable from the controller board, but you can leave it connected to the gripper motor on the other end, as it will already be in the right place. Now, plug in another 3-pin cable to the wrist roll motor and connect it to the controller board. As with the previous motor, make sure it is the only motor connected to the board and that the motor itself isn’t connected to any other one.

Repeat the operation for each motor as instructed.

<div style="
  margin:12px 0;
  padding:10px 16px;
  background:#050b14;                 /* dark background */
  border-radius:6px;
  border-left:4px solid #10b981;      /* green accent bar */
  color:#e5e7eb;
  font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  font-size:14px;
  line-height:1.5;
">
  Check your cabling at each step before pressing <strong>Enter</strong>.
  For instance, the power supply cable might disconnect as you manipulate the board.
</div>


When you are done, the script will simply finish, at which point the motors are ready to be used. You can now plug the 3-pin cable from each motor to the next one, and the cable from the first motor (the ‘shoulder pan’ with id=1) to the controller board, which can now be attached to the base of the arm.

<br>

<h3 align="center" style="font-size:30px;">Follower Servo Configuration</h3>

<div style="
  margin:12px 0;
  padding:8px 14px;
  background:#480b0b;
  border-radius:6px;
  border:1px solid #5c1515;
  color:#f9fafb;
  font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  font-size:13px;
">
  <div style="font-weight:700; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:4px; display:flex; align-items:center;">
    <span style="font-size:16px; margin-right:6px;">🔥</span>
    <span>Important</span>
  </div>
  <div>
    If you buy the Arm Kit version (ST-3215-C001), use a 5V power supply. If you buy the Arm Kit Pro version, please use a 12V power supply to calibrate the servo (ST-3215-C047/ST-3215-C018).
  </div>
</div>
<br>
<table style="width:100%; table-layout:fixed;">
  <thead>
    <tr>
      <th align="center" style="width:30%; max-width:260px;">Join Name</th>
      <th align="center" style="width:100%; max-width:260px;"><center>Reference Pic</center></th>
      <th align="center" style="width:100%; max-width:260px;"><center>Commands</center></th>
    </tr>
  </thead>
  <tbody>
    <!-- Gripper -->
    <tr>
      <td>
        <strong>Gripper</strong><br>
        <small>(Set id to 6)</small>
      </td>
      <td align="center">
      <br>
        <a href="..\assets\images\configure\Follower\gripper.png">
          <img
            src="..\assets\images\configure\Follower\gripper.png"
            alt="Follower_Gripper_Servo"
            style="width:100%; max-width:450px; border-radius:10px;"
          >
        </a>
        <div><code>Follower_Gripper_Servo_Config</code></div>
      </td>
      <td>
        <div><code>Instructions</code></div><br>
        You should see the following instruction<br>
        <div><code>Connect the controller board to the 'gripper' motor only and press enter.</code></div><br>
        As instructed, plug the gripper’s motor. Make sure it’s the only motor connected to the board, and that the motor itself is not yet daisy-chained to any other motor. As you press [Enter], the script will automatically set the id and baudrate for that motor.<br><br>
        You should then see the following message:<br>
         <div><code>'gripper' motor id set to 6</code></div>
      </td>
    </tr>
    <!-- Wrist_roll -->
    <tr>
      <td>
        <strong>Wrist_Roll</strong><br>
        <small>(Set id to 5)</small>
      </td>
      <td align="center">
      <br>
        <a href="..\assets\images\configure\Follower\wrist_roll.png">
          <img
            src="..\assets\images\configure\Follower\wrist_roll.png"
            alt="Follower_Wrist_Roll_Servo"
            style="width:100%; max-width:450px; border-radius:10px;"
          >
        </a>
        <div><code>Follower_Wrist_Roll_Servo_Config</code></div>
      </td>
      <td>
        <div><code>Instructions</code></div><br>
        You should see the following instruction<br>
        <div><code>Connect the controller board to the 'wrist_roll' motor only and press enter.</code></div><br>
        As instructed, plug the wrist roll’s motor. Make sure it’s the only motor connected to the board, and that the motor itself is not yet daisy-chained to any other motor. As you press [Enter], the script will automatically set the id and baudrate for that motor.<br><br>
        You should then see the following message:<br>
         <div><code>'wrist_roll' motor id set to 5</code></div>
      </td>
    </tr>
    <!-- Wrist_flex -->
    <tr>
      <td>
        <strong>Wrist_Flex</strong><br>
        <small>(Set id to 4)</small>
      </td>
      <td align="center">
      <br>
        <a href="..\assets\images\configure\Follower\wrist_flex.png">
          <img
            src="..\assets\images\configure\Follower\wrist_flex.png"
            alt="Follower_Wrist_Flex_Servo"
            style="width:100%; max-width:450px; border-radius:10px;"
          >
        </a>
        <div><code>Follower_Wrist_Flex_Servo_Config</code></div>
      </td>
      <td>
        <div><code>Instructions</code></div><br>
        You should see the following instruction<br>
        <div><code>Connect the controller board to the 'wrist_flex' motor only and press enter.</code></div><br>
        As instructed, plug the wrist flex’s motor. Make sure it’s the only motor connected to the board, and that the motor itself is not yet daisy-chained to any other motor. As you press [Enter], the script will automatically set the id and baudrate for that motor.<br><br>
        You should then see the following message:<br>
         <div><code>'wrist_flex' motor id set to 4</code></div>
      </td>
    </tr>
    <!-- Elbow_flex -->
    <tr>
      <td>
        <strong>Elbow_Flex</strong><br>
        <small>(Set id to 3)</small>
      </td>
      <td align="center">
      <br>
        <a href="..\assets\images\configure\Follower\elbow_flex.png">
          <img
            src="..\assets\images\configure\Follower\elbow_flex.png"
            alt="Follower_Elbow_Flex_Servo"
            style="width:100%; max-width:450px; border-radius:10px;"
          >
        </a>
        <div><code>Follower_Elbow_Flex_Servo_Config</code></div>
      </td>
      <td>
        <div><code>Instructions</code></div><br>
        You should see the following instruction<br>
        <div><code>Connect the controller board to the 'elbow_flex' motor only and press enter.</code></div><br>
        As instructed, plug the elbow flex’s motor. Make sure it’s the only motor connected to the board, and that the motor itself is not yet daisy-chained to any other motor. As you press [Enter], the script will automatically set the id and baudrate for that motor.<br><br>
        You should then see the following message:<br>
         <div><code>'elbow_flex' motor id set to 3</code></div>
      </td>
    </tr>
    <!-- Shoulder_lift -->
    <tr>
      <td>
        <strong>Shoulder_Lift</strong><br>
        <small>(Set id to 2)</small>
      </td>
      <td align="center">
      <br>
        <a href="..\assets\images\configure\Follower\shoulder_lift.png">
          <img
            src="..\assets\images\configure\Follower\shoulder_lift.png"
            alt="Follower_Shoulder_Lift_Servo"
            style="width:100%; max-width:450px; border-radius:10px;"
          >
        </a>
        <div><code>Follower_Shoulder_Lift_Servo_Config</code></div>
      </td>
      <td>
        <div><code>Instructions</code></div><br>
        You should see the following instruction<br>
        <div><code>Connect the controller board to the 'Shoulder_lift' motor only and press enter.</code></div><br>
        As instructed, plug the shoulder lift’s motor. Make sure it’s the only motor connected to the board, and that the motor itself is not yet daisy-chained to any other motor. As you press [Enter], the script will automatically set the id and baudrate for that motor.<br><br>
        You should then see the following message:<br>
         <div><code>'shoulder_lift' motor id set to 2</code></div>
      </td>
    </tr>
    <!-- Shoulder_pan -->
    <tr>
      <td>
        <strong>Shoulder_Pan</strong><br>
        <small>(Set id to 1)</small>
      </td>
      <td align="center">
      <br>
        <a href="..\assets\images\configure\Follower\shoulder_pan.png">
          <img
            src="..\assets\images\configure\Follower\shoulder_pan.png"
            alt="Follower_Shoulder_Lift_Servo"
            style="width:100%; max-width:450px; border-radius:10px;"
          >
        </a>
        <div><code>Follower_Shoulder_PAN_Servo_Config</code></div>
      </td>
      <td>
        <div><code>Instructions</code></div><br>
        You should see the following instruction<br>
        <div><code>Connect the controller board to the 'Shoulder_Pan' motor only and press enter.</code></div><br>
        As instructed, plug the shoulder pan’s motor. Make sure it’s the only motor connected to the board, and that the motor itself is not yet daisy-chained to any other motor. As you press [Enter], the script will automatically set the id and baudrate for that motor.<br><br>
        You should then see the following message:<br>
         <div><code>'shoulder_pan' motor id set to 1</code></div>
      </td>
    </tr>
 </tbody>
</table>

<h2>Leader</h2><br>
Do the same steps for the leader arm.<br>


```
lerobot-setup-motors \
    --teleop.type=so101_leader \
    --teleop.port=/dev/tty.usbmodem575E0031751  # <- paste here the port found at previous step
```

<br>
<h3 align="center" style="font-size:30px;">Leader Servo Configuration</h3>

<div style="
  margin:12px 0;
  padding:8px 14px;
  background:#480b0b;
  border-radius:6px;
  border:1px solid #5c1515;
  color:#f9fafb;
  font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  font-size:13px;
">
  <div style="font-weight:700; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:4px; display:flex; align-items:center;">
    <span style="font-size:16px; margin-right:6px;">🔥</span>
    <span>Important</span>
  </div>
  <div>
    Please use a 5V power supply for calibrating Leader motors (ST-3215-C046, C044, 001).
  </div>
</div>
<br>

<table>
    <tbody>
        <tr>
            <td>
               <img
                    src="..\assets\images\configure\Leader\gripper.jpg"
                    alt="Leader_Gripper_Servo_Config"
                    width="100%"
                    style="border-radius:12px; margin:0 8px;"
                > 
                <div align="center"><code>Leader_Gripper_Servo_Config</code></div>
            </td>
            <td>
               <img
                    src="../assets\images\configure\Leader\wrist_roll.jpg"
                    alt="Leader_Wrist_Roll_Servo_Config"
                    width="100%"
                    style="border-radius:12px; margin:0 8px;"
                >  
                <div align="center"><code>Leader_Wrist_Roll_Servo_Config</code></div>
            </td>
        </tr>
        <tr>
            <td>
               <img
                    src="..\assets\images\configure\Leader\wrist_flex.jpg"
                    alt="Leader_Wrist_Flex_Servo_Config"
                    width="100%"
                    style="border-radius:12px; margin:0 8px;"
                > 
                <div align="center"><code>Leader_Wrist_Flex_Servo_Config</code></div>
            </td>
            <td>
               <img
                    src="../assets\images\configure\Leader\elbow_flex.jpg"
                    alt="Leader_Elbow_Flex_Servo_Config"
                    width="100%"
                    style="border-radius:12px; margin:0 8px;"
                >  
                <div align="center"><code>Leader_Elbow_Flex_Servo_Config</code></div>
            </td>
        </tr>
        <tr>
            <td>
               <img
                    src="..\assets\images\configure\Leader\shoulder_lift.jpg"
                    alt="Leader_shoulder_lift_Servo_Config"
                    width="100%"
                    style="border-radius:12px; margin:0 8px;"
                > 
                <div align="center"><code>Leader_shoulder_lift_Servo_Config</code></div>
            </td>
            <td>
               <img
                    src="../assets\images\configure\Leader\shoulder_pan.jpg"
                    alt="Leader_Shoulder_Pan_Servo_Config"
                    width="100%"
                    style="border-radius:12px; margin:0 8px;"
                >  
                <div align="center"><code>Leader_Shoulder_Pan_Servo_Config</code></div>
            </td>
        </tr>
    </tbody>
</table>

<br>