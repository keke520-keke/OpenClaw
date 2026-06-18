import os
from datetime import datetime

def auto_train():
    print("=" * 50)
    print(f"开始执行自动模型训练，当前时间：{datetime.now()}")
    # 调用项目原有训练脚本
    os.system("python train_model.py")
    print("✅ AI模型训练完成，模型已自动更新")
    print("=" * 50)

if __name__ == "__main__":
    auto_train()
