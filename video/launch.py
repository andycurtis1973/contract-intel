#!/usr/bin/env python3
"""Launch the F5-TTS GPU worker to synthesize narration (nscale-learning pattern).

Voice (F5-TTS) runs on the AWS GPU worker; visuals + assembly are local
(assemble_local.py). Driven via boto3 so the clock-skew fix applies.

    python3 launch.py up     # upload script + runner, launch worker
    python3 launch.py wait   # poll S3, download all seg_NN.wav to video/audio/
    python3 launch.py run    # up + wait
"""

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
from _awsclock import ensure_clock_synced

AMI = "ami-0b9a79a750c641d95"
TYPE = "g4dn.xlarge"
KEY = "3xstrategykey"
SG = "sg-068d937cf94b5ff05"
SUBNET = "subnet-0e041501"
IAM = "video-pipeline-OrchestratorInstanceProfile-dQUZ1twvC9Ba"
BUCKET = "nscale-modules-641315376775-us-east-1"
PREFIX = "contract-intel-video"
REGION = "us-east-1"
N_SEGMENTS = 7


def _userdata() -> str:
    return f"""#!/bin/bash
exec > /var/log/ck_audio.log 2>&1
set -x
export PATH=/usr/local/bin:/usr/bin:/bin:/home/ubuntu/.local/bin:$PATH
sleep 10
nvidia-smi --query-gpu=name --format=csv,noheader || true
mkdir -p /opt/voices
aws s3 cp s3://{BUCKET}/voices/host_ref.wav /opt/voices/host_ref.wav
aws s3 cp s3://{BUCKET}/voices/expert_ref.wav /opt/voices/expert_ref.wav
chown -R ubuntu:ubuntu /opt/voices
aws s3 sync s3://{BUCKET}/code/ /home/ubuntu/
mkdir -p /home/ubuntu/ck_inputs
aws s3 sync s3://{BUCKET}/{PREFIX}/inputs/ /home/ubuntu/ck_inputs/
chown -R ubuntu:ubuntu /home/ubuntu/ck_inputs /home/ubuntu/worker.py
sudo -u ubuntu -H bash -c '
  source /home/ubuntu/podcast_pipeline/venv/bin/activate
  export CK_BUCKET={BUCKET} CK_PREFIX={PREFIX}
  export F5_VOICE_DIR=/opt/voices PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
  python3 -u /home/ubuntu/ck_inputs/make_audio_worker.py
'
aws s3 cp /var/log/ck_audio.log s3://{BUCKET}/{PREFIX}/audio/ck_audio.log || true
shutdown -h +1
"""


def up() -> str:
    ensure_clock_synced(REGION)
    import boto3

    s3 = boto3.client("s3", region_name=REGION)
    ec2 = boto3.client("ec2", region_name=REGION)
    A = HERE / "assets"
    # Clear any prior run's wavs so the poller can't grab stale output (race fix).
    for k in range(N_SEGMENTS):
        s3.delete_object(Bucket=BUCKET, Key=f"{PREFIX}/audio/seg_{k:02d}.wav")
    s3.upload_file(str(A / "script.json"), BUCKET, f"{PREFIX}/inputs/script.json")
    s3.upload_file(str(HERE / "make_audio_worker.py"), BUCKET, f"{PREFIX}/inputs/make_audio_worker.py")
    if (HERE / "expert_clean.wav").exists():
        s3.upload_file(str(HERE / "expert_clean.wav"), BUCKET, f"{PREFIX}/inputs/expert_clean.wav")
        print("uploaded script + runner + cleaned male reference")
    else:
        print("uploaded script + runner")
    iid = ec2.run_instances(
        ImageId=AMI, InstanceType=TYPE, KeyName=KEY,
        SecurityGroupIds=[SG], SubnetId=SUBNET,
        IamInstanceProfile={"Name": IAM},
        InstanceInitiatedShutdownBehavior="terminate",
        UserData=_userdata(), MinCount=1, MaxCount=1,
        BlockDeviceMappings=[{"DeviceName": "/dev/sda1",
                              "Ebs": {"VolumeSize": 200, "VolumeType": "gp3",
                                      "DeleteOnTermination": True}}],
        TagSpecifications=[{"ResourceType": "instance",
                            "Tags": [{"Key": "Name", "Value": "cache-is-king-audio"},
                                     {"Key": "Project", "Value": "cache-is-king-video"}]}],
    )["Instances"][0]["InstanceId"]
    print(f"launched GPU worker {iid} — F5-TTS narration (male voice) in progress")
    return iid


def wait() -> int:
    ensure_clock_synced(REGION)
    import boto3
    from botocore.exceptions import ClientError

    s3 = boto3.client("s3", region_name=REGION)
    audio = HERE / "audio"
    audio.mkdir(exist_ok=True)
    last = f"{PREFIX}/audio/seg_{N_SEGMENTS - 1:02d}.wav"
    print(f"polling for {N_SEGMENTS} narration wavs (boot ~3m, TTS ~6-10m)…")
    for i in range(80):
        try:
            s3.head_object(Bucket=BUCKET, Key=last)  # last wav => all done
            for k in range(N_SEGMENTS):
                key = f"{PREFIX}/audio/seg_{k:02d}.wav"
                s3.download_file(BUCKET, key, str(audio / f"seg_{k:02d}.wav"))
            print(f"\n  ✅ downloaded {N_SEGMENTS} wavs to {audio}")
            return 0
        except ClientError:
            time.sleep(30)
            print(f"  …{(i + 1) * 30}s", flush=True)
    print(f"\n  timed out. log: s3://{BUCKET}/{PREFIX}/audio/ck_audio.log")
    return 1


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "up":
        up(); return 0
    if cmd == "wait":
        return wait()
    if cmd == "run":
        up(); return wait()
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main())
