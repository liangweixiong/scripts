# _*_ coding: utf-8 _*_
_author__ = 'Aaron'
__time__ = '2018/3/16'

# _*_ coding: utf-8 _*_
_author__ = 'Aaron'
__time__ = '2018/3/15'

import logging
import os
from fabric.api import *
from fabric.contrib.files import append, exists
from fabric.colors import red, green


env.PROJECT_NAME = 'wenshu'
env.REMOTE_PROJECT_PATH = '/root/WenShuShengCheng'
env.LOCAL_PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


env.VIRTUALENV_NAME = env.PROJECT_NAME + "env"
env.VIRTUALENV_PATH = os.path.join("/usr/local/", env.VIRTUALENV_NAME)

env.LOCAL_SOFT = "/Users/Aaron/PycharmProjects/wenshuwork/install_script/software.tar.gz"
env.LOCAL_BASH = "/Users/Aaron/PycharmProjects/wenshuwork/install_script/script.tar.gz"
env.LOCAL_CONFIG = "/Users/Aaron/PycharmProjects/wenshuwork/install_script/config_dir"
env.REMOTE_SOFT_PATH = "/usr/local/src/software"
env.REMOTE_SCRIPT_PATH = "/usr/local/src/script"
env.REMOTE_CONFIG_PATH = "/usr/local/src/config"

env.hosts = ['172.16.146.157']
env.password = '123456'
env.user = 'root'


# 把所有需要的软件打包，放在本地software文件夹
# 把所有需要的脚本打包，放在本地script文件夹
# 远程端 /usr/local/src/software   /usr/local/src/script

def check_log(log_content):
    def decorator(func):
        def wrapper():
            result = func()
            with settings(hide('everything'), warn_only=True):
                if result.succeeded:
                    print(green(log_content))
                    logger.info(green(log_content))
                else:
                    print(red(log_content.replace("Success", "Failed")))
                    logger.info(red(log_content.replace("Success", "Failed")))

        return wrapper

    return decorator


def enter_vir_proj(func):
    def wrapper():
        with prefix("source %s/bin/activate" % env.VIRTUALENV_PATH):
            with cd(env.REMOTE_PROJECT_PATH):
                with settings(hide('everything'), warn_only=True):
                    func()

    return wrapper


@runs_once
def init_log():
    global logger
    fmt_date = '%Y-%m-%d %H:%M:%S.%s'
    fmt_content = '%(lineno)s %(asctime)s  [%(process)d]: %(levelname)s  %(filename)s  %(message)s'
    log_file = 'install_wenshu.log'
    logger = logging.getLogger('__name__')
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(log_file, mode='a')
    file_handler.setFormatter(logging.Formatter(fmt_content, fmt_date))
    logger.addHandler(file_handler)


def mk_dir():
    run("mkdir -p %s" % env.REMOTE_SOFT_PATH)
    run("mkdir -p %s" % env.REMOTE_SCRIPT_PATH)
    run("mkdir -p %s" % env.REMOTE_CONFIG_PATH)


# 把所有需要的软件打包，放在本地software,script文件夹
def send_to_remote():
    put(env.LOCAL_SOFT, env.REMOTE_SOFT_PATH)
    put(env.LOCAL_BASH, env.REMOTE_SCRIPT_PATH)
    put(env.LOCAL_CONFIG, env.REMOTE_CONFIG_PATH)


# 解压从本地传输过来的两个压缩包
def tar_xf_soft():
    with cd(env.REMOTE_SOFT_PATH):
        run("tar xf software.tar.gz")
    with cd(env.REMOTE_SCRIPT_PATH):
        run("tar xf script.tar.gz")


# 初始化linux
@check_log("Linux initialized Success!")
def linux_basic_config():
    with cd(env.REMOTE_SCRIPT_PATH):
        return run("/bin/bash deploy.sh")


# 安装python3
@check_log("Python3 installed Success!")
def python3_install():
    with cd(env.REMOTE_SCRIPT_PATH):
        return run("/bin/bash python3_install.sh")


# 安装Mysql5.7
@check_log("Mysql5.7 installed Success!")
def mysql57_install():
    with cd(env.REMOTE_SCRIPT_PATH):
        return run("python3 install_mysql57.py")


# 安装nginx
@check_log("Nginx installed Success!")
def nginx_install():
    with cd(env.REMOTE_SCRIPT_PATH):
        return run("/bin/bash nginx_install.sh")


def virtualenv_create():
    sudo("python3 -m venv " + env.VIRTUALENV_PATH)


@enter_vir_proj
def pip_requirements_install():
    run('pip install -r requirements.txt')


@enter_vir_proj
def django_initialize():
    run("mkdir -p static_root")
    run("python manage.py collectstatic --clear --noinput")
    run("python manage.py makemigrations")
    run("python manage.py migrate")


@enter_vir_proj
@check_log("Uwsgi installed Success!")
def uwsgi_install():
    sudo("pip install uwsgi")
    run("mkdir -p /var/log/uwsgi")
    run("touch /var/log/uwsgi/wenshu.log")


@check_log("DocxFactory installed Success!")
def docxfactory():
    with cd(env.REMOTE_SCRIPT_PATH):
        return run("/bin/bash docxfactory_install.sh")


def app_config_file():
    # nginx
    with cd("/usr/local/nginx/conf"):
        run("cp nginx.conf nginx.conf.bak")
        run("cp %s/nginx.conf ." % env.REMOTE_CONFIG_PATH)

    # mysql
    with cd(env.REMOTE_CONFIG_PATH):
        sudo("cp my.cnf /etc/")

        # uwsgi配置文件通过-i参数指定


def app_path_config():
    append("/etc/profile", "export PATH=$PATH:/usr/local/nginx/bin", use_sudo=True)
    append("/etc/profile", "export PATH=$PATH:/usr/local/mysql/bin", use_sudo=True)
    sudo("source /etc/profile")


def nginx_start():
    result = run("killall -9 nginx")
    if result.failed:
        run("nginx")
    else:
        print(green("nginx has been stopped"))


@enter_vir_proj
def uwsgi_start():
    result = run("killall -9 uwsgi")
    if result.failed:
        run("uwsgi -i %s" % (os.path.join(env.REMOTE_CONFIG_PATH, "wenshu.ini")))
    else:
        print(green("uwsgi has been stopped"))


def mysql_start():
    if exists("/data/mysql/data/Aaron.pid"):
        sudo("/etc/init.d/mysql stop")
    sudo("/etc/init.d/mysql start")


def deploy():
    init_log()
    mk_dir()
    send_to_remote()
    tar_xf_soft()
    linux_basic_config()
    python3_install()
    mysql57_install()

