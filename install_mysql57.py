# _*_ coding: utf-8 _*_

_author__ = 'Aaron Liang'
__time__ = '2018/3/5'

import os
import shlex
import pymysql
import re
import shutil
import tarfile
import stat
import logging
import subprocess
import click

try:
    import configparser
except ImportError:
    import Configparser as configparser

logger = None
MYSQL_DATA_DIR = '/data/mysql/'
MYSQL_INSTALL_DIR = '/usr/local/mysql/'
MYSQL_STARTUP_SCRIPT = '/etc/init.d/mysql'
MY_CNF_FILE = '/etc/my.cnf'
MYSQL_ERROR_LOG = '/data/mysql/logs/error.log'


def mk_log():
    global logger
    fmt_date = '%Y-%m-%d %H:%M:%S.%s'
    fmt_content = '%(lineno)s %(asctime)s  [%(process)d]: %(levelname)s  %(filename)s  %(message)s'
    log_file = 'install_mysql.log'
    logger = logging.getLogger('__name__')
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(log_file, mode='a')
    file_handler.setFormatter(logging.Formatter(fmt_content, fmt_date))
    logger.addHandler(file_handler)


@click.command()
@click.option('-P', '--port', default='3306', help='port 3306')
@click.option('-t', "--tarpkg", default='/usr/local/src/mysql-5.7.21-linux-glibc2.12-x86_64.tar.gz',
              help='tarfile /usr/local/src/mysql-5.7.21-linux-glibc2.12-x86_64.tar.gz')
def opt_config(port, tarpkg):
    click.echo("mysql installation start!")

    if (port and str.isdigit(port)) and (tarpkg and os.path.isfile(tarpkg)):
        mysql_port = port
        mysql_install_file = tarpkg

    else:
        print('%s -h' % __file__)
        raise SystemExit('%s -h' % __file__)

    if not os.path.exists('/etc/my.cnf'):
        logger.info('step1:please add /etc/my.cnf')
    logger.info('step1: Check /etc/my.cnf SUCCESS!')

    make_dir(mysql_port)
    logger.info('step2: Make directory SUCCESS!')

    extract(mysql_install_file)
    logger.info('step3:Extract tarfile SUCCESS!')

    move_tared_dir(mysql_install_file)
    logger.info('step4:Copy file SUCCESS!')

    chown()
    logger.info('step5:Chown SUCCESS!')

    mysql_install()
    logger.info('step6:Mysql_install SUCCESS!')

    set_env()
    logger.info('step7:Set global env SUCCESS!')

    modify_startup_script()
    logger.info('step8:Modify startup script SUCCESS!')

    mysql_service_start()
    logger.info('step9:Start mysql service SUCCESS!')

    mysql_pwd = get_mysql_pwd()
    logger.info('step10:Get mysql_pwd SUCCESS!')
    logger.info('------->' + mysql_pwd)

    logger.info('Congratulations! Mysql has been installed successfully!')


# 创建必要的目录
def make_dir(port):
    if os.path.exists('/data/mysql/mysql%s/data' % port):
        logger.error('mysql %s already install' % port)
        raise SystemExit('mysql %s already install' % port)

    try:
        os.makedirs('/data/mysql/data')
        os.makedirs('/data/mysql/tmp')
        os.makedirs('/data/mysql/logs')
    except Exception as e:
        logger.error(e)


# 解压二进制安装包
def extract(mysql_install_file):  # /usr/local/src/mysql-5.7.21-linux-glibc2.12-x86_64.tar.gz
    if not os.path.exists(mysql_install_file):
        logger.error('%s does not exists' % mysql_install_file)
        raise SystemExit('%s does not exists' % mysql_install_file)
    os.chdir(os.path.dirname(mysql_install_file))  # /usr/local/src/
    with tarfile.open(mysql_install_file, 'r:gz') as t:
        t.extractall(".")  # 解压到当前目录/usr/local/src/


# 拷贝安装包文件到程序目录
def move_tared_dir(mysql_install_file):
    tared_mysql_install_dir = mysql_install_file.split('.tar.gz')[0]
    # /usr/local/src/mysql-5.7.21-linux-glibc2.12-x86_64
    shutil.move(tared_mysql_install_dir, "/usr/local/")
    # os.chdir(MYSQL_INSTALL_DIR)  # /usr/local/mysql
    new_mysql_dir = os.path.join("/usr/local/", os.path.basename(tared_mysql_install_dir))
    os.symlink(new_mysql_dir, "/usr/local/mysql")
    shutil.copy2(os.path.join(MYSQL_INSTALL_DIR, 'support-files/mysql.server'), MYSQL_STARTUP_SCRIPT)


# 修改安装目录和数据目录权限
def chown():
    exit_code = subprocess.call(shlex.split("id mysql"))
    # 如果exit_code为0，则mysql用户存在
    if exit_code:
        subprocess.call(shlex.split("groupadd mysql"))
        subprocess.call(shlex.split("useradd -s /sbin/nologin -g mysql -M mysql"))

    subprocess.call(shlex.split("chown -R mysql:mysql /data"))
    subprocess.call(shlex.split("chown -R mysql:mysql %s" % MYSQL_INSTALL_DIR))


# 设置环境变量
def set_env():
    add_content = '\nexport PATH=$PATH:/usr/local/mysql/bin\n'
    with open('mysql', 'a+') as f:
        re_obj = re.compile(r'.*/usr/local/mysql/bin.*')
        flag = True
        f.seek(0)
        for line in f:
            if re_obj.search(line):
                flag = False
        if flag:
            f.write(add_content)

    os.system("source /etc/profile")


# 初始化mysql
def mysql_install():
    if os.path.exists(MY_CNF_FILE):
        # cmd = "/usr/local/msyql/bin/mysqld --defaults-file=/etc/my.cnf  --initialize --user=mysql --basedir=/usr/local/mysql --datadir=/data/mysql"
        cmd = MYSQL_INSTALL_DIR + "bin/mysqld --defaults-file=%s  --initialize --user=mysql --basedir=/usr/local/mysql --datadir=/data/mysql/data" % MY_CNF_FILE
        p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if stdout:
            logger.info('Install output: %s' % (stdout))
        if stderr:
            logger.error('Install error output: %s' % (stderr))
        if p.returncode == 0:
            logger.info('Initialize SUCCESS!')
        else:
            logger.info('Initialize failed , please check the /data/mysql/logs/error.log')
            raise SystemExit('Initialize failed , please check the /data/mysql/logs/error.log')
    else:
        logger.error(MY_CNF_FILE + ' does not esixts')
        raise SystemExit(MY_CNF_FILE + ' does not esixts')


# 2018-03-05T09:59:30.644198Z 1 [Note] A temporary password is generated for root@localhost: %nm,Pxfuk2yG

# 获取mysql密码
def get_mysql_pwd():
    mysql_pwd = ""
    with open(MYSQL_ERROR_LOG, "r") as f:
        re_obj = re.compile(".*A temporary password.*root@localhost: (.*)\n")
        for line in f:
            mysql_pwd_match = re_obj.search(line)
            if mysql_pwd_match:
                mysql_pwd = mysql_pwd_match.group(1)
                break
    if not mysql_pwd:
        logger.info("Password has not been found")
    return mysql_pwd


# 设置启动脚本
def modify_startup_script():
    re_obj_datadir = re.compile('^datadir=')
    re_obj_basedir = re.compile('^basedir=')
    with open(MYSQL_STARTUP_SCRIPT, "a") as f:
        for line in f:
            re_obj_datadir.sub('datadir=%s/data' % MYSQL_DATA_DIR, line)
            re_obj_basedir.sub('basedir=%s' % MYSQL_INSTALL_DIR, line)

    # 设置启动脚本执行权限
    stmode = os.stat(MYSQL_STARTUP_SCRIPT).st_mode
    os.chmod(MYSQL_STARTUP_SCRIPT, stmode | stat.S_IXOTH | stat.S_IXGRP | stat.S_IXUSR)


def mysql_service_start():
    cmd = "/etc/init.d/mysql start"
    result_code = subprocess.call(shlex.split(cmd))

    if result_code == 0:
        logger.info('Mysql start up SUCCESS!')

    else:
        logger.error('Mysql startup failed , please check the /data/mysql/logs/error.log')
        raise SystemExit('Mysql startup failed , please check the /data/mysql/logs/error.log')


if __name__ == '__main__':
    mk_log()
    opt_config()
