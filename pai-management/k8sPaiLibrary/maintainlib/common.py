# Copyright (c) Microsoft Corporation
# All rights reserved.
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
# to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED *AS IS*, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
# BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import print_function
#
import yaml
import os
import errno
import sys
import subprocess
import jinja2
import argparse
import paramiko
import tarfile
import socket
import logging
import time
import etcd
import logging.config


logger = logging.getLogger(__name__)


def load_yaml_file(path):

    with open(path, "r") as f:
        file_data = yaml.load(f)

    return file_data



def execute_shell(shell_cmd, error_msg):

    try:
        subprocess.check_call( shell_cmd, shell=True )

    except subprocess.CalledProcessError:
        logger.error(error_msg)
        sys.exit(1)




def execute_shell_return(shell_cmd, error_msg):

    try:
        subprocess.check_call( shell_cmd, shell=True )

    except subprocess.CalledProcessError:
        logger.warning(error_msg)
        return False

    return True




def read_template(template_path):

    with open(template_path, "r") as fin:
        template_data = fin.read().decode('utf-8')

    return template_data



def generate_from_template(template_data, cluster_config, host_config):

    generated_file = jinja2.Template(template_data).render(
        {
            "hostcofig": host_config,
            "clusterconfig": cluster_config['clusterinfo'],
            "cluster": cluster_config
        }
    )

    return generated_file



def generate_from_template_dict(template_data, map_table):

    generated_file = jinja2.Template(template_data).render(
        map_table
    )

    return generated_file



def write_generated_file(generated_file, file_path):

    with open(file_path, "w+") as fout:
        fout.write(generated_file)



def ipv4_address_validation(ipv4_addr):
    return True

def port_validation(port):

    if str(port).isdigit() == True and int(port) >= 0 and int(port) <= 65535 :

        ret = True

    else:

        ret = False
        logger.error("{0} is not a correct port. A port can only contain digits!".format(str(port)))

    return ret



def sftp_paramiko(src, dst, filename, host_config):
    hostip = str(host_config['hostip'])
    if ipv4_address_validation(hostip) == False:
        return False

    username = str(host_config['username'])
    password = str(host_config['password'])
    port = 22
    if 'sshport' in host_config:
        if port_validation(host_config['sshport']) == False:
            return False
        port = int(host_config['sshport'])

    # First make sure the folder exist.
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=hostip, port=port, username=username, password=password)

    stdin, stdout, stderr = ssh.exec_command("sudo mkdir -p {0}".format(dst), get_pty=True)
    stdin.write(password + '\n')
    stdin.flush()
    for response_msg in stdout:
        print(response_msg.encode('utf-8').strip('\n'))

    ssh.close()

    # Put the file to target Path.
    transport = paramiko.Transport((hostip, port))
    transport.connect(username=username, password=password)

    sftp = paramiko.SFTPClient.from_transport(transport)
    sftp.put('{0}/{1}'.format(src, filename), '{0}/{1}'.format(dst, filename))
    sftp.close()

    transport.close()

    return True


# Support command with sudo? : No
# Could you get the command result as the return value? : No
def ssh_shell_paramiko(host_config, commandline):
    result_stdout, result_stderr = ssh_shell_paramiko_with_result(host_config, commandline)
    if result_stdout is None or result_stderr is None:
        return False
    return True


# Support command with sudo? : No
# Could you get the command result as the return value? : Yes
def ssh_shell_paramiko_with_result(host_config, commandline):
    hostip = str(host_config['hostip'])
    if ipv4_address_validation(hostip) == False:
        return False
    username = str(host_config['username'])
    password = str(host_config['password'])
    port = 22
    if 'sshport' in host_config:
        if port_validation(host_config['sshport']) == False:
            return (None, None)
        port = int(host_config['sshport'])
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=hostip, port=port, username=username, password=password)
    stdin, stdout, stderr = ssh.exec_command(commandline, get_pty=True)
    logger.info("Executing the command on host [{0}]: {1}".format(hostip, commandline))
    result_stdout = ""
    for response_msg in stdout:
        result_stdout += response_msg
        print(response_msg.encode('utf-8').strip('\n'))
    result_stderr = ""
    for response_msg in stderr:
        result_stderr += response_msg
    ssh.close()
    return (result_stdout, result_stderr)


# Support command with sudo? : Yes
# Could you get the command result as the return value? : No
def ssh_shell_with_password_input_paramiko(host_config, commandline):

    hostip = str(host_config['hostip'])
    if ipv4_address_validation(hostip) == False:
        return False

    username = str(host_config['username'])
    password = str(host_config['password'])
    port = 22
    if 'sshport' in host_config:
        if port_validation(host_config['sshport']) == False:
            return False
        port = int(host_config['sshport'])

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=hostip, port=port, username=username, password=password)
    stdin, stdout, stderr = ssh.exec_command(commandline, get_pty=True)
    stdin.write(password + '\n')
    stdin.flush()
    logger.info("Executing the command on host [{0}]: {1}".format(hostip, commandline))
    for response_msg in stdout:
        print (response_msg.encode('utf-8').strip('\n'))

    ssh.close()
    return True



def get_user_dir(host_config):

    cmd = "getent passwd {0} | cut -d: -f6".format(str(host_config['username']))
    result_stdout, result_stderr = ssh_shell_paramiko_with_result(host_config, cmd)
    if result_stdout != None:
        ret = result_stdout.encode('unicode-escape').decode('string_escape')
        ret = ret.replace('\n', '')
        ret = ret.replace('\r', '')
        return ret

    if str(host_config['username']) == "root":
        return "/root"
    else:
        return "/home/{0}".format(host_config["username"])



def create_path(path):

    if not os.path.exists("{0}".format(path)):

        try:
            os.makedirs(path)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise



def archive_tar(target, path):

    tar = tarfile.open(target, "w")

    for root,dir,files in os.walk(path):
        for file in files:
            fullpath = os.path.join(root, file)
            tar.add(fullpath)

    tar.close()



def maintain_package_wrapper(cluster_config, maintain_config, node_config, jobname):

    create_path("parcel-center/{0}/{1}".format(node_config['nodename'], jobname))

    if "template-list" in maintain_config[jobname]:
        for template_info in maintain_config[jobname]["template-list"]:

            name = template_info['name']
            src = template_info['src']
            dst = template_info['dst']

            template_data = read_template("{0}".format(src))
            template_file = generate_from_template(template_data, cluster_config, node_config)
            create_path("parcel-center/{0}/{1}".format(node_config['nodename'], dst))
            write_generated_file(template_file, "parcel-center/{0}/{1}/{2}".format(node_config['nodename'], dst, name))

    if "file-list" in maintain_config[jobname]:
        for file_info in maintain_config[jobname]["file-list"]:

            name = file_info['name']
            src = file_info['src']
            dst = file_info['dst']
            create_path("parcel-center/{0}/{1}".format(node_config['nodename'], dst))
            execute_shell(
                "cp {0} parcel-center/{1}/{2}/{3}".format(src, node_config['nodename'], dst, name),
                "Failed copy {0} parcel-center/{1}/{2}/{3}".format(src, node_config['nodename'], dst, name)
            )

    execute_shell("cp -r parcel-center/{0}/{1} .".format(node_config['nodename'], jobname), "Failed cp job folder")
    archive_tar("parcel-center/{0}/{1}.tar".format(node_config['nodename'], jobname), jobname)
    execute_shell("rm -rf {0}".format(jobname), "Failed to remove {0}".format(jobname))



def maintain_package_cleaner(node_config):

    execute_shell(
        "rm -rf parcel-center/{0}".format(node_config['nodename']),
        "Failed to remove parcel-center/{0}".format(node_config['nodename'])
    )



def get_etcd_leader_node(cluster_config):

    # Get leader node.
    host_list = list()

    for host in cluster_config['mastermachinelist']:
        host_list.append((cluster_config['mastermachinelist'][host]['hostip'], 4001))

    client = etcd.Client(host=tuple(host_list), allow_reconnect=True)

    etcdid = client.leader['name']
    for host in cluster_config['mastermachinelist']:
        if etcdid == cluster_config['mastermachinelist'][host]['etcdid']:
            logger.debug("Current leader of etcd-cluster: {0}".format(cluster_config['mastermachinelist'][host]))
            return cluster_config['mastermachinelist'][host]

    logger.error("Can't find the leader of etcd.")
    return None



def get_new_etcd_peer_ip_list(cluster_config, new_node_config):

    etcd_cluster_ips_peer = ""
    separated = ""

    host_list = list()
    for host in cluster_config['mastermachinelist']:
        host_list.append((cluster_config['mastermachinelist'][host]['hostip'], 4001))

    client = etcd.Client(host=tuple(host_list), allow_reconnect=True)

    member_dict = client.members
    for member_hash in member_dict:

        etcd_id = member_dict[member_hash]['name']
        peer_url = member_dict[member_hash]['peerURLs'][0]

        if etcd_id == "":
            # new member before announcing, etcdid will be empty.
            continue

        ip_peer = "{0}={1}".format(etcd_id, peer_url)
        etcd_cluster_ips_peer = etcd_cluster_ips_peer + separated + ip_peer
        separated = ","


    if new_node_config != None:

        new_etcd_id = new_node_config['etcdid']
        peer_url = new_node_config['hostip']
        ip_peer = "{0}=http://{1}:2380".format(new_etcd_id, peer_url)
        etcd_cluster_ips_peer = etcd_cluster_ips_peer + separated + ip_peer

        logger.debug("New etcd-initial-cluster: {0}".format(etcd_cluster_ips_peer))

    return etcd_cluster_ips_peer



def get_etcd_peer_ip_list(cluster_config):

    return get_new_etcd_peer_ip_list(cluster_config)