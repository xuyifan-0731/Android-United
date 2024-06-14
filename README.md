# Android United: Developing and Evaluating Android Agents in A Reproducible Environment

This repo is an anonymous repository for reviewing the paper Android United. 

The Android Eval evaluation set and evaluation code used in the paper have already been released. Since the training data and evaluation images are still undergoing privacy and harmful information checks, the training data, evaluation images, and training result checkpoints are temporarily unavailable. We promise to make all training data and checkpoints public after the paper is accepted.

Chinese version of this README is available [here](README_CN.md).

# Pipeline Usage

## Evaluation Preset

The evaluation environment will be set in a specific time and space. The current time is set to: 2024.5.10 12:00, and the location is: a station near Stanford University in San Francisco. Every time it starts running, it will reposition to the above time and space.

## Auto Evaluation Pipeline

1. Install Android Studio on your machine, and start a virtual machine to ensure that the adb command is properly installed.
2. Download the avd.zip and ini files. Extract the avd.zip file and place it along with the ini file in `/Users/your user name/.android/avd`. Modify the ini file as follows:

```ini
avd.ini.encoding=UTF-8
path=/Users/your user name/.android/avd/Pixel_7_Pro_API_33.avd
path.rel=avd/Pixel_7_Pro_API_33.avd
target=android-33
```

If necessary, modify parts of the paths in the config.ini and hardware-qemu.ini files under `Pixel_7_Pro_API_33.avd` to match your corresponding paths. The method for using the image has not been fully determined yet; a script will be written once it stabilizes.

File download link:

Run the following code, then check in Android Studio -> Virtual Devices Manager to see if there is a `Pixel_7_Pro_API_33` image and make sure it can start normally. However, please do not make any changes to the image. Note to modify the avd and sdk paths to the correct paths.
```python
python modify_mobile.py 
    --avd_dir /Users/UserName/.android/avd 
    --sdk_dir /Users/UserName/Library/Android/sdk 
    --device_name Pixel_7_Pro_API_33
```

3. Configure the emulator

Run the following commands:
```bash
echo 'export ANDROID_SDK_HOME=/path/to/your/android/sdk' >> ~/.zshrc && source ~/.zshrc
echo 'export PATH=$PATH:/path/to/your/android/sdk/emulator' >> ~/.zshrc && source ~/.zshrc
```
If you are using bash instead of zsh, replace `~/.zshrc` with `~/.bash_profile`.

4. Create a yaml file in the project directory with the following content:

```yaml
agent:
    name: OpenAIAgent
    args:
        api_key: sk-
        api_base: "https://one-api.glm.ai/v1"
        model_name: "gpt-4-1106-preview"
        max_new_tokens: 512

task:
    class: TextOnlyMobileTask_AutoTest
    args:
        save_dir: "./logs/evaluation"
        max_rounds: 25
        request_interval: 3

eval:
    avd_base: /Users/your user name/.android/avd
    avd_name: Pixel_7_Pro_test_device
    avd_log_dir: ./logs/avd
    android_sdk_path: /Users/your user name/Library/Android/sdk
```

Here, `/Users/your user name/.android/avd` is the default location where Android Studio stores images, `avd_name` is the standard test image name, `avd_log_dir` is the directory for storing output results, and `android_sdk_path` is the location of the Android SDK.

5. Run the following commands

To test the text+xml scheme, run:
```bash
python text_only_auto_test.py -n test_name -c your path to config.yaml
```

The specific output of each question is saved under `./logs/evaluation/test_name`, and the evaluation results are saved in the `output` folder.
If you only want to run a few questions for testing, you can refer to:

```bash
python text_only_auto_test.py -n test_name -c your path to config.yaml --task_id taskid_1,taskid_2,taskid_3
```

To test the multimodal model scheme, run:
```bash
python screenshot_auto_test.py -n test_name -c your path to config.yaml
```

The corresponding task_id for each question can be found in `evaluation/config`.

If you need to generate complete metric results, you need to add the `--detail_metrics` parameter in `evaluation_auto_test.py`.

Before generating the evaluation results, you need to add the `glm4 key` in `definition.py` as the model for judging QA questions. The location for filling in is at line 97. #TODO: Modify the filling method.

Use the following code to generate a single evaluation result:
```bash
python evaluation_auto_test.py --input_dir ./logs/evaluation/test_name
```
You can also use
```bash
python evaluation_all.py --input_folder xx --output_folder xx --output_excel xx
```
to directly generate the results of all models and save them to an excel file.

## How to Modify the Backbone Model

The `Agent` class has been predefined in the `agent/` folder, with implementations for the OpenAI interface based on oneapi and the currently deployed GLM interface. If you need to add a base model, you need to:

1. Create a new Python file under `agent/`, and refer to `agent/model/OpenAIAgent` to implement your model call by inheriting the `Agent` class. The `act` function input is already organized in the OpenAI message format, and the output is a string. If the input format of the corresponding model is different from OpenAI, you can refer to the `format_history` function in `glm_model` for modifications. The `prompt_to_message` method modifies the current round of prompts and image inputs (if any) to the current model's single-round format, which can refer to the standard OpenAI format provided by `OpenAIAgent`.
2. Import your new class in `agent/__init__.py`.
3. Replace the content under `agent` in the config file used by `text_only_auto_test.py` with:

```yaml
agent:
    name: Your Agent Module Name
    args:
        max_new_tokens: 512
```

Make sure the name matches your implemented class name, and the content under `args` will be passed to your class's `init` function.

## Steps to Add a New Task

During the process of writing a new task, it is equally important to write and use the code to determine if your code is correct through actual running results. Therefore, please follow the steps below to ensure each new task is error-free.

1. Write your task. Tasks include yaml files, evaluation methods, and corresponding mobile app installation.
   1. The task's yaml file should refer to other existing files under `evaluation/configs` and must include `task_id`, `task`, `metric_type`, and `metric_func`. `adb_query` is only used when the results need to be queried using adb commands. Although `category` is not yet in use, it is strongly recommended to add it.
   2. The evaluation method needs to inherit the `evaluation/task/SingleTask` class. After each recorded operation, the `judge` function will be executed, and its return value is a dict: `{"judge_page": bool, "1": bool, ..., "complete": bool}`. The code will record the judgment result of the last page where `judge_page` is `True`, and `complete` should only be set to `True` if all judgment points are correct. If it's a task that compares return values, the `check_answer` method has already been implemented. Modify `final_ground_truth` to the standard answer before calling this function.
   3. Refer to other tasks, import all evaluation methods in `evaluation/app_name/__init__.py` into the `function_map` class.
   4. To ensure the model can execute the launch command correctly, add the app name and corresponding package name in `templates/packages/apps_dict`. The package name can be obtained by executing `adb -s {device} shell dumpsys window | grep mCurrentFocus | awk -F '/' '{print $1}' | awk '{print $NF}'`.
2. Execute your task using at least the most advanced agent and generate evaluation results. If necessary, quickly complete the correct operation during model operation intervals to ensure that the recorded operation can capture the correct result page between two model operations to test if your code can complete the detection task.
3. Use the `check_result_multiprocess.py` function to generate screenshots of each step. Focus on checking whether the screenshots of correct model operations are indeed judged as correct.
```
