import sys
import os
import shutil
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
import re
import git


# TODO:用命令自变量或标准输入来改写变量

# 用户变量

# Overleaf的项目ID，用户ID
# 1. 在latex编辑画面中打开开发者工具
# 2. 在控制台进行以下输入后输出的是项目ID、用户ID
# > project_id
# "5f8d2f5e40a9cd007604f46b"
# > user_id
# "5f8f784af6e341007b878a51"
#

# 書き換え必須 ✅
PROJECT_ID = '5f8d2f5e40a9cd007604f46b'  # プロジェクトを一意に決める

# 書き換え必須 ✅
USER_ID = '5f8f784af6e341007b878a51'  # ユーザを一意に決める

# 書き換え必須 ✅
GITHUB_USER_NAME = 'TakuKitamura'  # GitHubのID

# 書き換え必須 ✅
GITHUB_REPO_NAME = 'verified-mqtt-parser-paper'  # Overleafプロジェクトをホスティングしたいリポジトリ名

# NginxのAccessログのパス, 書き換えの必要が出るかもしれない
NGINX_LOG_PATH = '/var/log/nginx/access.log'

# 書き換えが必要かもしれない
GIT_BRANCH_NAME = 'master'  # GitHubリポジトリ上でホスティングするブランチ名


# 書き換えが必要かもしれない
PAPER_DIR_NAME = 'overleaf'  # リポジトリルートに作成されるディレクトリ名

# 書き換えが必要かもしれない
EXCLUDE_LIST = './exclude_list'  # OverLeafプロジェクトから余計なファイルがPUSHされた場合は, ここに追加する

###


WATCH_OVERLEAF_PATH = '/var/lib/sharelatex/data/compiles/{}-{}'.format(
    PROJECT_ID, USER_ID)  # OverLeafプロジェクトが保存されているPATH

GITHUB_REPO_URL = 'https://github.com/{}/{}.git'.format(
    GITHUB_USER_NAME, GITHUB_REPO_NAME)  # ホスティング先のリポジトリ


# PUSHするディレクトリ
COPYED_DIR_PATH = '{}/{}'.format(GITHUB_REPO_NAME, PAPER_DIR_NAME)


def print_err(any_el: any) -> None:
    """
    stderrへ出力を行う
    """
    print(any_el, file=sys.stderr)
    exit(1)


def get_exclude_list() -> list:
    """
    OverLeafプロジェクト内でpushしないファイル/ディレクトリリストを取得
    """
    exclude_list = []
    with open(EXCLUDE_LIST, 'r') as f:
        exclude_list = f.read().splitlines()
    return exclude_list


def get_nginx_access_log():
    """
    nginxのログを取得
    """
    log_list = []
    with open(NGINX_LOG_PATH, 'r') as f:
        log_list = f.read().splitlines()
    return log_list


def get_watch_overleaf_list() -> list:
    """
    OverLeafプロジェクト内のファイル/ディレクトリリスト
    """
    return os.listdir(WATCH_OVERLEAF_PATH)


def ready_repo() -> git.Repo:
    """
    git管理プロジェクトが存在しないなら, Cloneしgit管理プロジェクトを扱えるように準備する
    """
    if (not os.path.isdir(GITHUB_REPO_NAME)):
        git.Repo.clone_from(url=GITHUB_REPO_URL, to_path=GITHUB_REPO_NAME)
    return git.Repo(GITHUB_REPO_NAME)


def main(argc: int, argv: list) -> None:
    """
    main関数
    """
    print('[READY REPO]')
    repo = ready_repo()
    # print('[PULL]')
    # repo.git.pull()
    print('[CHECKOUT]')
    repo.git.checkout(GIT_BRANCH_NAME)

    # 初始化overleaf项目被保存的目录
    watch_overleaf_list = get_watch_overleaf_list()
    exclude_list = get_exclude_list()
    if(not os.path.isdir(COPYED_DIR_PATH)):
        os.mkdir(COPYED_DIR_PATH)
    else:
        # 虽然速度下降，但将删除所有保存overleaf项目的目录
        shutil.rmtree(COPYED_DIR_PATH)
        os.mkdir(COPYED_DIR_PATH)

    print('[PROJECT COPY]')
    for file_or_dir in watch_overleaf_list:
        if (file_or_dir not in exclude_list):
            watch_overleaf_file_or_dir = '{}/{}'.format(
                WATCH_OVERLEAF_PATH, file_or_dir)
            copyed_path = '{}/{}'.format(
                COPYED_DIR_PATH, file_or_dir)

            # 上書きコピー
            if os.path.isfile(watch_overleaf_file_or_dir):  # ファイルコピー
                shutil.copy2(watch_overleaf_file_or_dir, copyed_path)
            elif os.path.isdir(watch_overleaf_file_or_dir):  # ディレクトリコピー
                shutil.copytree(watch_overleaf_file_or_dir, copyed_path)
            else:
                print_err("{}'s path is invalid".format(
                    watch_overleaf_file_or_dir))
    # ファイル変更がある場合
    if (len(repo.index.diff(None)) > 0 or len(repo.untracked_files) > 0):
        print('[ADD]')
        # プロジェクト全てをステージング
        repo.git.add(all=True)
        # UTCをJSTに変換しその文字列を取得
        today_jst_str = datetime.now(timezone.utc).astimezone(
            timezone(timedelta(hours=+9))).strftime('%Y年%m月%d日%H時%M分%S秒')
        print('[COMMIT]')
        commit_diff = repo.git.diff(repo.head.commit.tree)
        repo.index.commit('[WatchOverleaf]||{}||\n\n{}'.format(
            today_jst_str, commit_diff))
        print('[PUSH]')
        repo.remote(name='origin').push()
    print('[DONE]')


if __name__ == '__main__':
    # 命令行参数
    argv = sys.argv
    argc = len(argv)
    last_update_date = datetime(2020, 1, 1, 0, 0).astimezone(
        timezone(timedelta(hours=+9)))
    while True:
        # TODO: 这里要依赖日志的格式，一不小心可能会掉下来。需要测试
        # 从日志的后面进行探测
        for line in reversed(get_nginx_access_log()):
            # ex. ['192.168.1.1', '-', '-', '[19/Oct/2020:07:31:47', '+0000]', 'GET', '/project/5f8d2f5e40a9cd007604f46b/user/5f8cdf0540a9cd007604f453/build/1753fc578c4-433e012c62ebc28d/output/output.pdf?compileGroup=standard&pdfng=true', 'HTTP/1.1', '200', '36782', 'http://192.168.1.62/project/5f8d2f5e40a9cd007604f46b', 'Mozilla/5.0', '(Macintosh;', 'Intel', 'Mac', 'OS', 'X', '10_15_7)', 'AppleWebKit/537.36', '(KHTML,', 'like', 'Gecko)', 'Chrome/86.0.4240.99', 'Safari/537.36']
            splited = line.replace('"', '').split(' ')
            request_date = datetime.strptime(
                splited[3][1:], '%d/%b/%Y:%H:%M:%S').astimezone(
                timezone(timedelta(hours=+9)))
            method = splited[5]
            request_path = urlparse(splited[6])[2]
            status = splited[8]

            # 捕捉PDF显示的时间
            if (
                request_date > last_update_date and  # 如果有新的Request跳转到API
                method == 'GET' and
                re.match(r'/project/{}/user/{}/build/.+/output/output.pdf'.format(PROJECT_ID, USER_ID), request_path) and
                status == '200'
            ):
                main(argc, argv)
                print('{} -> {}\n'.format(last_update_date, request_date))
                last_update_date = request_date
                break
        time.sleep(1)  # 日志探测间隔
