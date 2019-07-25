from django.conf import settings
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect, HttpResponse
import re
from celery_tasks.tasks import send_register_active_email
from django.contrib.auth import authenticate, login
# 安装itsdangerous库  pip3 install itsdangerous
from django.views.generic import View
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, SignatureExpired
from user.models import User


# /user/register
def register(request):
    '''注册'''
    if request.method == 'GET':
        # 显示注册页面
        return render(request, 'register.html')
    else:
        # 进行注册处理
        # 接收数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        # 进行数据校验
        if not all([username, password, email]):
            # 数据不完整
            # return HttpResponse("数据不完整")
            return render(request, 'register.html', {'errmsg': '数据不完整'})
        # 校验二次 密码是否一样

        # 校验邮箱
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})
        # 是否同意协议
        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})
        # 校验用户名是否重复
        try:
            user = User.objects.get(username=username)  # user为真的就代表用户名已存在
        except User.DoesNotExist:
            # 用户名不存在
            user = None

        if user:
            # 用户名已存在
            return render(request, 'register.html', {'errmsg': '用户名已存在'})
        # 进行业务处理: 进行用户注册(这里使用django自带的注册用户方法
        user = User.objects.create_user(username, email, password)
        user.is_active = 0  # 刚注册的用户不应该是激活的,这里要手动改为不激活,值为0
        user.save()  # 保存下来

        # 发送激活邮件, 包含激活链接: http://127.0.0.1:8000/user/active/3
        # 激活链接中需要包含用户的身份信息,并且要把身份信息进行加密

        # 加密用户的身份信息,生成激活token
        serializer = Serializer(settings.SECRET_KEY, 300)
        # 加密user.id
        info = {'confirm': user.id}
        # token = serializer.dump(info)
        # 返回应答
        return redirect(reverse('goods:index'))  # 反向解析,返回首页


# /user/register
class RegisterView(View):
    '''注册'''

    def get(self, request):
        '''显示注册页面'''
        return render(request, 'register.html')

    def post(self, request):
        '''进行注册处理'''
        # 接收数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        # 进行数据校验
        if not all([username, password, email]):
            # 数据不完整
            # return HttpResponse("数据不完整")
            return render(request, 'register.html', {'errmsg': '数据不完整'})
        # 校验二次 密码是否一样

        # 校验邮箱
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})
        # 是否同意协议
        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})
        # 校验用户名是否重复
        try:
            user = User.objects.get(username=username)  # user为真的就代表用户名已存在
        except User.DoesNotExist:
            # 用户名不存在
            user = None

        if user:
            # 用户名已存在
            return render(request, 'register.html', {'errmsg': '用户名已存在'})
        # 进行业务处理: 进行用户注册(这里使用django自带的注册用户方法
        user = User.objects.create_user(username, email, password)
        user.is_active = 0  # 刚注册的用户不应该是激活的,这里要手动改为不激活,值为0
        user.save()  # 保存下来

        # 发送激活邮件, 包含激活链接: http://127.0.0.1:8000/user/active/3
        # 激活链接中需要包含用户的身份信息,并且要把身份信息进行加密

        # 加密用户的身份信息,生成激活token
        serializer = Serializer(settings.SECRET_KEY, 1000)
        # 加密user.id
        info = {'confirm': user.id}
        token = serializer.dumps(info)
        # print(token) # 是b类型二进制
        token = token.decode()  # 默认是utf-8
        print(token)

        # celery发邮件
        send_register_active_email.delay(email, username, token)
        # 启动celery的worker 复制一份项目代码到redis端 命令:celery -A celery_tasks.tasks worker -l info

        '''
        # 一般阻塞发邮件
        # subject = '天天生鲜欢迎你'
        # message = ''  # 不能发送有样式的html内容,所以用html_message
        # sender = settings.EMAIL_FROM  # 发件人
        # receiver = [email]  # 收件人邮箱(列表) post请求接受注册信息的email
        # html_message = '<h1>%s, 欢迎您成为天天生鲜注册会员</h1>请点击下面链接激活你的帐号<br/><a href= "http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s"</a>' % (
        #                username, token, token)
        # send_mail(subject, message, sender, receiver, html_message=html_message)  # 传入以上的参数
        '''
        # 返回应答, 跳转到首页
        return redirect(reverse('goods:index'))  # 反向解析,返回首页


class ActiveView(View):
    '''用户激活'''

    def get(self, request, token):
        '''进行用户激活
        token: 请求url返回来的加密信息
        '''
        # 进行解密,获取要激活的用户信息
        serializer = Serializer(settings.SECRET_KEY, 1000)
        try:
            info = serializer.loads(token)
            # 获取待激活用户的id
            user_id = info['confirm']  # 加密时: info = {'confirm' : user.id}
            # 根据id获取用户信息
            user = User.objects.get(id=user_id)
            user.is_active = 1  # 1 代表激活用户
            user.save()  # 更新数据
            # 跳转到登录页面
            return redirect(reverse('user:login'))  # 反向解析到login页面
        except SignatureExpired as e:
            # 激活链接已过期
            return HttpResponse('激活链接已过期')


# /user/login
class LoginView(View):
    '''登录'''

    def get(self, request):
        '''显示登录页面'''
        # 判断是否记住了用户名
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ""
            checked = ""

        # 使用模板
        return render(request, 'login.html', {'username': username, 'checked': checked})

    def post(self, request):
        '''登录校验'''
        # 接收数据
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        # 校验数据
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': '数据不完整'})

        # 业务处理:登录校验
        user = authenticate(username=username, password=password)  # 使用django自带的校验
        if user is not None:
            # 用户名密码正确
            if user.is_active:
                # 用户已激活
                # 记录用户的登录状态
                login(request, user)

                # 跳转到首页
                response = redirect(reverse('goods:index')) # HttpResponseRedirect

                # 判 是否需要記住用名
                remember = request.POST.get('remember')
                if remember == 'on':
                    # 记住用户名
                    response.set_cookie('username', username, max_age=7*24*3600) # 设置cookie
                else:
                    response.delete_cookie('username') # 删除cookie
                # 返回response
                return response

            else:
                # 用户未激活
                return render(request, 'login.html', {'errmsg': '账户未激活'})
        else:
            # 用户名或密码错误
            return render(request, 'login.html', {'errmsg': '用户名或密码错误'})
        # 返回应答
