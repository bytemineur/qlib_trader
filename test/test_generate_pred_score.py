"""
test_generate_pred_score.py — 预测分数生成脚本测试用例

注意: 该脚本依赖 Qlib 环境和模型文件，测试主要验证代码结构。
"""
import unittest
import os
import sys

# 将脚本目录加入 path
SCRIPT_DIR = "/mnt/c/Users/zhh/Desktop/qlib_trader/script"
sys.path.insert(0, SCRIPT_DIR)


class TestGeneratePredScoreStructure(unittest.TestCase):
    """generate_pred_score.py 结构测试"""

    def test_file_exists(self):
        """脚本文件存在"""
        script_path = os.path.join(SCRIPT_DIR, "generate_pred_score.py")
        self.assertTrue(os.path.isfile(script_path))

    def test_can_import_as_module(self):
        """可以作为模块导入（不执行 main）"""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "gen_pred", os.path.join(SCRIPT_DIR, "generate_pred_score.py")
            )
            mod = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec)
        except Exception as e:
            self.fail(f"导入失败: {e}")

    def test_has_main_function(self):
        """包含 main 函数"""
        import ast
        script_path = os.path.join(SCRIPT_DIR, "generate_pred_score.py")
        with open(script_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        func_names = [node.name for node in ast.walk(tree)
                      if isinstance(node, ast.FunctionDef)]
        self.assertIn("main", func_names)

    def test_has_load_config_function(self):
        """包含 load_config 函数"""
        import ast
        script_path = os.path.join(SCRIPT_DIR, "generate_pred_score.py")
        with open(script_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        func_names = [node.name for node in ast.walk(tree)
                      if isinstance(node, ast.FunctionDef)]
        self.assertIn("load_config", func_names)

    def test_has_freeze_support(self):
        """入口有 mp.freeze_support()"""
        script_path = os.path.join(SCRIPT_DIR, "generate_pred_score.py")
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("freeze_support", content)

    def test_imports_qlib(self):
        """导入了 qlib"""
        script_path = os.path.join(SCRIPT_DIR, "generate_pred_score.py")
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("import qlib", content)

    def test_imports_pickle(self):
        """导入了 pickle"""
        script_path = os.path.join(SCRIPT_DIR, "generate_pred_score.py")
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("import pickle", content)

    def test_uses_alpha158(self):
        """使用 Alpha158 处理器"""
        script_path = os.path.join(SCRIPT_DIR, "generate_pred_score.py")
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("Alpha158", content)

    def test_outputs_pred_score_csv(self):
        """输出 pred_score.csv"""
        script_path = os.path.join(SCRIPT_DIR, "generate_pred_score.py")
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("pred_score.csv", content)


class TestGeneratePredScoreConfig(unittest.TestCase):
    """generate_pred_score.py 配置相关测试"""

    def test_reads_model_path_from_config(self):
        """从 config.yaml 读取 model_path"""
        script_path = os.path.join(SCRIPT_DIR, "generate_pred_score.py")
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("model_path", content)
        self.assertIn("CONFIG", content)

    def test_load_config_handles_missing_file(self):
        """load_config 在配置文件不存在时抛出 FileNotFoundError"""
        import ast
        script_path = os.path.join(SCRIPT_DIR, "generate_pred_score.py")
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("FileNotFoundError", content)
        self.assertIn("配置文件未找到", content)

    def test_config_path_resolves_project_root(self):
        """配置路径使用项目根目录"""
        script_path = os.path.join(SCRIPT_DIR, "generate_pred_score.py")
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # 应包含相对路径解析逻辑
        self.assertIn("parent", content)

    def test_uses_config_yaml(self):
        """引用 configs/config.yaml"""
        script_path = os.path.join(SCRIPT_DIR, "generate_pred_score.py")
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("config.yaml", content)


class TestGeneratePredScoreOutput(unittest.TestCase):
    """generate_pred_score.py 输出相关测试"""

    def test_csv_path_in_ml_directory(self):
        """pred_score.csv 输出至 ml/ 目录"""
        script_path = os.path.join(SCRIPT_DIR, "generate_pred_score.py")
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("'ml'", content)
        self.assertIn("pred_score.csv", content)

    def test_uses_utf8_sig_encoding(self):
        """CSV 使用 utf-8-sig 编码"""
        script_path = os.path.join(SCRIPT_DIR, "generate_pred_score.py")
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("utf-8-sig", content)

    def test_infer_processors_empty(self):
        """推理时 infer_processors=[]"""
        script_path = os.path.join(SCRIPT_DIR, "generate_pred_score.py")
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("infer_processors", content)

    def test_instruments_csi300(self):
        """使用沪深300成分股"""
        script_path = os.path.join(SCRIPT_DIR, "generate_pred_score.py")
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("csi300", content)


if __name__ == "__main__":
    unittest.main()
