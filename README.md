# Android United: Developing and Evaluating Android Agents in A Reproducible Environment

This repo is an anonymous repository for reviewing the paper Android United.

The Android Eval evaluation set and evaluation code used in the paper have already been released. Since the training
data and evaluation images are still undergoing privacy and harmful information checks, the training data, evaluation
images, and training result checkpoints are temporarily unavailable. We promise to make all training data and
checkpoints public after the paper is accepted.

A visual example is provided in the `visual_example` folder.

<!--Chinese version of this README is available [here](README_CN.md).-->

# Pipeline Usage

## Evaluation Preset

The evaluation environment will be set in a specific time and space. The current time is set to: 2024.5.10 12:00, and
the location is: a station near Stanford University in San Francisco. Every time it starts running, it will reposition
to the above time and space.

## Auto Evaluation Pipeline

We offer two testing methods: AVD on Mac (arm64) and Docker on Linux (x86_64).

### Prepare the Environment

If you use AVD on Mac (arm64), please refer to [here](docs/prepare_for_mac.md) to set up the environment.

If you use Docker on Linux (x86_64), please refer to [here](docs/prepare_for_linux.md) to set up the environment.

### Run the Auto Evaluation Pipeline

To test, run:

```bash
python eval.py -n test_name -c your path to config.yaml
```

The specific output of each question is saved under `./logs/evaluation/test_name`, and the evaluation results are saved
in the `output` folder.
If you only want to run a few questions for testing, you can refer to:

```bash
python eval.py -n test_name -c your path to config.yaml --task_id taskid_1,taskid_2,taskid_3
```

If you are using Docker for testing, we support parallel testing. Please note that you need to confirm in advance that
you have sufficient memory and storage. Each concurrent session takes up approximately 6G of memory and 9G of storage
space.

```bash
python eval.py -n test_name -c your path to config.yaml -p 3
```

The corresponding task_id for each question can be found in `evaluation/config`.

Use the following code to generate a single evaluation result:

```bash
python generate_result.py --input_dir ./logs/evaluation/ --output_dir ./logs/evaluation/ --output_excel ./logs/evaluation/test_name.xlsx --key "your glm4 key"
```

You need to fill in your glm4 key in the --key parameter, which can be applied for on the glm4 official website.
generate_result.py will generate an Excel file of all test results under --input_ir, containing detailed results for
each question.

## How to Modify the Backbone Model

The `Agent` class has been predefined in the `agent/` folder, with implementations for the OpenAI interface based on
oneapi and the currently deployed GLM interface. If you need to add a base model, you need to:

1. Create a new Python file under `agent/`, and refer to `agent/model/OpenAIAgent` to implement your model call by
   inheriting the `Agent` class. The `act` function input is already organized in the OpenAI message format, and the
   output is a string. If the input format of the corresponding model is different from OpenAI, you can refer to
   the `format_history` function in `glm_model` for modifications. The `prompt_to_message` method modifies the current
   round of prompts and image inputs (if any) to the current model's single-round format, which can refer to the
   standard OpenAI format provided by `OpenAIAgent`.
2. Import your new class in `agent/__init__.py`.
3. Replace the content under `agent` in the config file used by `text_only_auto_test.py` with:

```yaml
agent:
    name: Your Agent Module Name
    args:
        max_new_tokens: 512
```

Make sure the name matches your implemented class name, and the content under `args` will be passed to your
class's `init` function.

## Steps to Add a New Task

During the process of writing a new task, it is equally important to write and use the code to determine if your code is
correct through actual running results. Therefore, please follow the steps below to ensure each new task is error-free.

1. Write your task. Tasks include yaml files, evaluation methods, and corresponding mobile app installation.
    1. The task's yaml file should refer to other existing files under `evaluation/config` and must
       include `task_id`, `task`, `metric_type`, and `metric_func`. `adb_query` is only used when the results need to be
       queried using adb commands. Although `category` is not yet in use, it is strongly recommended to add it.
    2. The evaluation method needs to inherit the `evaluation/task/SingleTask` class. After each recorded operation,
       the `judge` function will be executed, and its return value is a
       dict: `{"judge_page": bool, "1": bool, ..., "complete": bool}`. The code will record the judgment result of the
       last page where `judge_page` is `True`, and `complete` should only be set to `True` if all judgment points are
       correct. If it's a task that compares return values, the `check_answer` method has already been implemented.
       Modify `final_ground_truth` to the standard answer before calling this function.
    3. Refer to other tasks, import all evaluation methods in `evaluation/app_name/__init__.py` into the `function_map`
       class.
    4. To ensure the model can execute the launch command correctly, add the app name and corresponding package name
       in `templates/packages/apps_dict`. The package name can be obtained by
       executing `adb -s {device} shell dumpsys window | grep mCurrentFocus | awk -F '/' '{print $1}' | awk '{print $NF}'`.
2. Execute your task using at least the most advanced agent and generate evaluation results. If necessary, quickly
   complete the correct operation during model operation intervals to ensure that the recorded operation can capture the
   correct result page between two model operations to test if your code can complete the detection task.
3. Use the `tools/check_result_multiprocess.py` function to generate screenshots of each step. Focus on checking whether
   the screenshots of correct model operations are indeed judged as correct.

## Steps to Change AVD Snapshot

If you want to define a mobile snapshot different from the android eval snapshot, you need to follow these steps:

1. Download related docker files from the
   link: https://drive.google.com/file/d/1xpPEzVof5hrt5bQY6BHm_4Uoyq5mJQNb/view?usp=drive_link
2. Extract the file, enter the extracted folder, and then run:

```bash
docker build -t android_eval_no_avd:latest .
```

3. Configure your AVD snapshot on an x86_64 machine (it is recommended to configure it directly using Android Studio).
   Note that the default installed Android AVD type is:

```dockerfile
RUN /bin/bash -c "source /root/.bashrc && yes | sdkmanager 'platform-tools' 'emulator' 'system-images;android-33;google_apis;x86_64'"
RUN /bin/bash -c "source /root/.bashrc && yes | sdkmanager 'build-tools;33.0.0'"
RUN /bin/bash -c "source /root/.bashrc && yes | sdkmanager 'platforms;android-33'"
```

If you want to configure the AVD for a different version, please modify the specific version number installed in the
Dockerfile. Note that the version number must be strictly consistent, otherwise, the installed image will not be able to
read the existing cache.

4. You can use the following code to generate the AVD image used in the docker:

```python
python tools/modify_mobile_to_docker.py 
    --avd_dir /Path/to/your/.android/avd 
    --device_name your device name 
    --save_dir /Path/to/your/save/avd
```

Alternatively, you can modify it as follows:

Find your .avd folder and .ini file through Android Studio -> Virtual Devices Manager -> Right-click -> Show on Disk,
and make the following modifications:

In Pixel_7_Pro_API_33.ini, modify path and path.rel to the following paths:

```ini
avd.ini.encoding=UTF-8
path=/root/.android/avd/device name.avd
path.rel=avd/device name.avd
target=android-33
```

In Pixel_7_Pro_API_33.avd/config.ini, modify the following paths:

```ini
...
image.sysdir.1 = system-images/android-33/google_apis/x86_64/
...
skin.path = /root/.android/skins/pixel_7_pro
...
```

Keep the other contents unchanged.

5. Start an image and copy your .avd folder and .ini file into the image:

```bash
docker run -it  android_eval_no_avd:latest /bin/bash 
docker cp /path/to/your/device name.avd container_id:/root/.android/avd
docker cp /path/to/your/device name.ini container_id:/root/.android/avd
```

After completing the above, you can execute the following in the image:

```bash
emulator -avd device name -no-window -no-audio -no-snapshot-save
```

Verify whether the installation is successful.




