# Android United: Developing and Evaluating Android Agents in A Reproducible Environment

本repo是论文Android United的审稿使用匿名repo。在论文被接受后，将会公开所有代码，数据和模型。
目前论文所用的Android Eval评测集和评测代码已经全部公布。由于训练数据和评测镜像还在进行隐私和有害信息检查，因此训练数据，评测镜像和训练结果checkpoint暂时不公开。我们承诺在论文被接受后公开所有训练数据和checkpoint。

英文版本的README可在[这里](README.md)查看。



# Pipeline Usage

## 评测预设定

评测环境将被设定在一个确定的时空环境。目前时间定位为：2024.5.10 12:00，空间定位为：旧金山市斯坦福大学旁某车站。每次开始运行都会重新定位到以上时空位置。

## Auto Evaluation Pipeline

1. 在你的机器上安装android studio，并且启动一个虚拟机，确保adb指令正常安装
2. 下载avd.zip和ini文件，将avd.zip文件解压后，与ini文件一起放在/Users/your user name/.android/avd下，并且修改ini文件为：

```ini
avd.ini.encoding=UTF-8
path=/Users/your user name/.android/avd/Pixel_7_Pro_API_33.avd
path.rel=avd/Pixel_7_Pro_API_33.avd
target=android-33
```

必要的时候，请修改Pixel_7_Pro_API_33.avd下config.ini和hardware-qemu.ini文件内部分路径修改为你的对应路径。还没有完全确定镜像的使用方法，稳定后会编写成一个脚本

文件下载地址：


运行以下代码，然后请在android studio->Virtual devices manager中查看是否有Pixel_7_Pro_API_33这个镜像，并且确定能正常启动。但是请不要对镜像做任何修改。注意修改avd和sdk为正确的路径。
```python
python modify_mobile.py 
    --avd_dir /Users/UserName/.android/avd 
    --sdk_dir /Users/UserName/Library/Android/sdk 
    --device_name Pixel_7_Pro_API_33
```

3. 配置emulator

运行以下指令：
```bash
echo 'export ANDROID_SDK_HOME=/path/to/your/android/sdk' >> ~/.zshrc && source ~/.zshrc
echo 'export PATH=$PATH:/path/to/your/android/sdk/emulator' >> ~/.zshrc && source ~/.zshrc
```
如果你使用的是 bash 而不是 zsh，可以将 ~/.zshrc 替换为 ~/.bash_profile。


4. 参考以下文件，在项目目录创建一个yaml文件，填写以下内容

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

其中，/Users/your user name/.android/avd是android studio默认的镜像放置位置，avd_name是标准测试镜像名称，avd_log_dir是输出结果存放位置，android_sdk_path是android sdk的位置

5. 运行以下命令

如果想要测试文本+xml方案，运行：
```bash
python text_only_auto_test.py -n test_name -c your path to config.yaml
```

每道题的具体输出保存在./logs/evaluation/test_name下，评测结果保存在output文件夹中。
如果你只想运行几道题进行测试，可以参考：

```bash
python text_only_auto_test.py -n test_name -c your path to config.yaml --task_id taskid_1,taskid_2,taskid_3
```

如果要测试多模态模型方案，运行：
```bash
python screenshot_auto_test.py -n test_name -c your path to config.yaml
```

其中，task_id对应的具体题目在evaluation/config中查询。

如果需要生成完整的metric结果，需要在evaluation_auto_test.py添加--detail_metrics参数。

在生成评测结果前，你需要在definition.py中添加glm4 key作为判断QA问题的模型。填写位置在第97行。#TODO: 修改填写方法

使用以下代码生成单条评测结果：
```bash
python evaluation_auto_test.py --input_dir ./logs/evaluation/test_name
```
你也可以直接使用
```bash
python evaluation_all.py --input_folder xx --output_folder xx -outout_excel xx
```
直接生成全部模型的结果并且储存至excel中。

## 修改backbone model的方法

在agent/文件夹下已经预设了Agent类，并且给出了基于oneapi的openai接口以及目前部署的glm接口两种实现。如果需要增加基座模型，则你需要：

1. 在agent下新建一个py文件，参考agent/model/OpenAIAgent继承Agent类实现你的模型调用。其中act函数输入为已经组织好的openai message格式，输出为字符串。如果对应的模型输入格式与openai不同，可以参考glm_model的format_history函数进行修改。prompt_to_message方法将当轮prompt和图片输入（如有）修改为当前模型当单轮格式，可以参考OpenAIAgent提供当标准openai格式。
2. 在``agent/__init__.py``中导入你新增的类
3. 在运行text_only_auto_test.py用到的config文件中，将agent下的内容替换为：

```	
agent:
    name: Your Agnet Module Name
    args:
        max_new_tokens: 512
```

其中你需要确保name与你实现的类名一致，且args下的内容都会被传至你的类init函数中。


## 增加新任务的步骤

在编写新任务的过程中，按一定格式编写和利用实际运行结果判断你的代码是否正确同样重要。因此每一个增加的任务请都参照以下流程确定无误。

1. 编写你的任务。任务包括yaml文件，评测方法和对应的手机app安装。
   1. 任务的yaml文件参考evaluation/configs下其他已有文件，必须包含task_id，task，metric_type和metric_func。adb_query仅在结果需要使用adb指令查询时使用。category暂时没有用上，但是强烈建议添加
   2. 评测方法需要继承evaluation/task/SingleTask类。其中，每次被记录的操作之后都会执行judge函数，其返回值是一个dict:{"judge_page":bool, "1":bool,...,"complete":bool}。代码中将会记录最后一个judge_page为True的页面的判断结果，只有全部判断点都正确的情况下，complete才应该被设置为True。如果是比对返回值类型的题目，已经实现了check_answer方法。在调用前先修改final_ground_truth为标准答案，再调用这一函数即可。
   3. 参考其他几个任务，在``evaluation/app_name/__init__.py``下将全部评测方法导入类function_map中。
   4. 为了让模型能够正确执行launch指令，需要在templates/packages/apps_dict里添加app名称和对应的package包名。包名可以通过执行```adb -s {device} shell dumpsys window | grep mCurrentFocus | awk -F '/' '{print $1}' | awk '{print $NF}'```获取。
2. 至少使用目前最先进的agent执行你的任务，并且生成评测结果。必要的时候可以在模型操作间歇快速的完成正确操作，确保两个模型操作之间记录操作的时候能够记录到你认为的正确结果页面，以检测你的代码是否能够完成检测任务。
3. 使用check_result_multiprocess.py函数生成每一步的操作截图。重点检查模型执行正确的截图是否确实被判断为正确。



