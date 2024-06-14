import yaml
import importlib


class AppConfig:
    def __init__(self, file_path, output_dir = None):
        self.file_path = file_path
        self.data = None
        self.metrics = {}
        self.task_name = {}
        self.metrics_type = {}
        self.command_per_step = {}
        self.output_dir = output_dir
        self.load_params()

    def load_params(self):
        try:
            with open(self.file_path, 'r') as file:
                self.data = yaml.safe_load(file)
                self.APP = self.data.get('APP')
                self.package = self.data.get('package')
                if 'tasks' in self.data:
                    for task in self.data['tasks']:
                        func_name = task.get('metric_func')
                        task_id = task.get('task_id')
                        metric_type = task.get('metric_type')
                        if func_name:
                            app_module_name = func_name.split('.')[1]
                            module = importlib.import_module(f'evaluation.{app_module_name}')
                            if hasattr(module, 'function_map') and task_id in module.function_map:
                                task['metric_func'] = module.function_map[task_id]
                                self.metrics[task_id] = task['metric_func']
                                self.metrics_type[task_id] = metric_type
                                self.task_name[task_id] = task.get('task')
                                if task.get("adb_query"):
                                    self.command_per_step[task_id] = task.get("adb_query")
                            else:
                                print(f"No valid function mapped for {task_id}")
                                task['metric_func'] = None
        except FileNotFoundError:
            print("Error: The file was not found.")
        except yaml.YAMLError as exc:
            print(f"Error in YAML file formatting: {exc}")
        except Exception as e:
            import traceback
            print(traceback.print_exc())

    def get_tasks(self):
        if self.data:
            return self.data.get('tasks', [])
        return []

    def get_metrics(self):
        return self.metrics


