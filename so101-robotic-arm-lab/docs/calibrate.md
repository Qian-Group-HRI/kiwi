<h1 align="center">SO-ARM101 Arms Calibrate</h1>
<br>
<div><code>Calibrate</code></div><br>
Next, you’ll need to calibrate your robot to ensure that the leader and follower arms have the same position values when they are in the same physical position. The calibration process is very important because it allows a neural network trained on one robot to work on another.
<br><br>
<div><code>Follower</code></div><br>
Run the following command or API example to calibrate the follower arm:
<br>
<br>

```
    lerobot-calibrate \
    --robot.type=so101_follower \
    --robot.port=/dev/tty.usbmodem58760431551 \ # <- The port of your robot
    --robot.id=my_awesome_follower_arm # <- Give the robot a unique name
```
<br>
<br>
The demonstration below shows how to perform the calibration. First you need to move the robot to the position where all joints are in the middle of their ranges. Then after pressing enter you have to move each joint through its full range of motion.<br>
<br>
<div align="center">
    <a href="..\assets\images\Calibrate\calibrate_so101_2.mp4">
        <img src="..\assets\images\Calibrate\calibrate.gif">
    </a>
</div>

<br>
<div><code>Leader</code></div><br>
Do the same steps to calibrate the leader arm, run the following command or API example:
<br>

```
    lerobot-calibrate \
    --teleop.type=so101_leader \
    --teleop.port=/dev/tty.usbmodem58760431551 \ # <- The port of your robot
    --teleop.id=my_awesome_leader_arm # <- Give the robot a unique name
```

<h1 align="center">Congrats 🎉, your robot is all set to learn a task on its own.</h1>