"""
Flask应用启动文件
"""
import os
from app import create_app, db
from config import get_config

# 创建Flask应用
app = create_app()

@app.shell_context_processor
def make_shell_context():
    """Flask shell上下文"""
    from app.models import QAPair, Category, UploadHistory
    return {
        'db': db,
        'QAPair': QAPair,
        'Category': Category,
        'UploadHistory': UploadHistory
    }

if __name__ == '__main__':
    # 开发环境启动配置
    config_class = get_config()
    debug = config_class.DEBUG
    
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5001)),
        debug=debug
    )