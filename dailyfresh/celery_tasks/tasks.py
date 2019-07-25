# 使用celery
from celery import Celery
from django.conf import settings
from django.core.mail import send_mail

# 创建一个Celery类的实例对象
app = Celery('celery_tasks.tasks', broker='redis://127.0.0.1:6379/1')

# 定义任务函数
@app.task
def send_register_active_email(to_email, username, token):
    '''发送激活邮件'''
    # 组织邮件信息
    subject = '天天生鲜欢迎你'
    message = ''  # 不能发送有样式的html内容,所以用html_message
    sender = settings.EMAIL_FROM  # 发件人
    receiver = [to_email]  # 收件人邮箱(列表) post请求接受注册信息的email
    html_message = '<h1>%s, 欢迎您成为天天生鲜注册会员</h1>请点击下面链接激活你的帐号<br/><a href= "http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s"</a>' % (
        username, token, token)
    send_mail(subject, message, sender, receiver, html_message=html_message)  # 传入以上的参数
