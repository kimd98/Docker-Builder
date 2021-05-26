from __future__ import print_function

import subprocess
import os.path
import time
import sys
import shutil
from xml.etree import ElementTree
import struct
import tempfile
import re

cmd_environ = os.environ.copy()
paths = {'OUT':None, 'BIN':None, 'SCRIPT':None, 'TMP':None, 'WD':os.getcwd()}
start_time = time.time()

values = {'--bct': 'P3448_A00_lpddr4_204Mhz_P987.cfg', '--bct_cold_boot': None, '--key': ['None'], '--encrypt_key': None, '--cfg': 'flash.xml', 
'--bl': 'cboot.bin', '--board': None, '--eeprom': None, '--cmd': 'sign; write DTB ./signed/kernel_tegra210-p3448-0002-p3449-0000-b00.dtb.encrypt; reboot', 
'--instance': None, '--bpfdtb': None, '--hostbin': None, '--applet': 'nvtboot_recovery.bin', '--dtb': None, '--bldtb': 'kernel_tegra210-p3448-0002-p3449-0000-b00.dtb', 
'--kerneldtb': None, '--chip': '0x21', '--out': None, '--nct': None, '--fb': None, '--odmdata': '0xa4000', '--lnx': None, '--tos': None, '--eks': None, 
'--boardconfig': None, '--skipuid': False, '--securedev': False, '--keyindex': None, '--keep': False, '--wb': None, '--bl-load': None, '--bins': None, '--dev_params': None, 
'--sdram_config': None, '--ramcode': None, '--misc_config': None, '--misc_cold_boot_config': None, '--pinmux_config': None, '--pmc_config': None, '--pmic_config': None, 
'--gpioint_config': None, '--uphy_config': None, '--scr_config': None, '--scr_cold_boot_config': None, '--br_cmd_config': None, '--prod_config': None, '--device_config': None, 
'--applet-cpu': None, '--bpf': None, '--mb1_bct': None, '--mb1_cold_boot_bct': None, '--skipsanitize': False, '--tegraflash_v2': False, '--chip_major': '0', '--nv_key': None, 
'--nvencrypt_key': None, '--cl': '39314184', '--soft_fuses': None, '--deviceprod_config': None, '--rcm_bct': 'P3448_A00_lpddr4_204Mhz_P987.cfg', '--secureboot': False, 
'--mem_bct': None, '--mem_bct_cold_boot': None, '--minratchet_config': None, '--wb0sdram_config': None, '--blversion': None, '--ratchet_blob': None, '--output_dir': None, 
'--applet_softfuse': None, '--ignorebfs': None, '--trim_bpmp_dtb': False, '--external_device': False}

tegrarcm_values = { '--list':'rcm_list.xml', '--signed_list':'rcm_list_signed.xml',
                    '--storage_info':'storage_info.bin', '--board_info':'board_info.bin',
                    '--chip_info':'chip_info.bin', '--rollback_data':'rollback_data.bin',
                    '--fuse_info': 'blow_fuse_data.bin', '--read_fuse':'read_fuse.bin',
                    '--get_fuse_names': 'read_fuse_names.txt',
                  }
tegrabct_values = { '--bct':None, '--bct_cold_boot':None, '--list':'bct_list.xml', '--signed_list':'bct_list_signed.xml', '--mb1_bct':None, '--mb1_cold_boot_bct':None, '--membct_cold_boot': None, '--membct_rcm' : None, '--rcm_bct': None, '--updated': False }
tegrasign_values = { '--pubkeyhash':'pub_key.key', '--mode':'None', '--getmontgomeryvalues': 'montgomery.bin'}
tegraparser_values = { '--pt':None, '--ufs_otp':'ufs_otp_data.bin'}
tegrahost_values = { '--list':'images_list.xml', '--signed_list':'images_list_signed.xml', '--ratchet_blob':'ratchet_blob.bin'}

tegraflash_binaries_v2 = { 'tegrabct':'tegrabct_v2', 'tegrahost':'tegrahost_v2', 'tegrasign':'tegrasign_v2', 'tegrarcm':'tegrarcm_v2', 'tegradevflash':'tegradevflash_v2', 'tegraparser':'tegraparser_v2', 'dtc':'dtc'}

tegraflash_binaries = { 'tegrabct':'tegrabct', 'tegrahost':'tegrahost', 'tegrasign':'tegrasign', 'tegrarcm':'tegrarcm', 'tegradevflash':'tegradevflash', 'tegraparser':'tegraparser', 'dtc':'dtc'}

tegraflash_eeprom_name_map = {
    '0x18' : {
        'boardinfo' : 'cvm',
        'baseinfo' : 'cvb'
    },
    '0x19' : {
        'boardinfo' : 'cvm',
        'baseinfo' : 'cvb'
    }
}

# A helper function in do_sign before calling tegraflash_sign (not used)
def tegraflash_update_env():

    path_separator = ":"
    if sys.platform == 'win32':
        path_separator = ";"

    cmd_environ["PATH"] = paths['BIN'] + path_separator + paths['WD'] + path_separator + paths['OUT'] \
                                  + path_separator + paths['SCRIPT'] + path_separator + paths['TMP'] + path_separator + os.environ["PATH"]

def _parse_fuses(filename):
    with open(filename, 'rb') as f:
        # TID shall be the first 4 bytes of fuses.bin
        tid = struct.unpack('>I',  f.read(4))[0] # Expected to be read in Big Endian format
        info_print('TID Read from Device: %x\n' % tid)

# Data used below is referred from tegrabl_sigheader.h
def _is_header_present(file_path):
    file_size = os.path.getsize(file_path)
    # File size less than 400 (header size) means header is not present
    if file_size < 400:
        info_print('%s size is less than header size (400)\n' % file_path)
        return False

    header_magic_fmt = '>I'
    header_magic_size = struct.calcsize(header_magic_fmt)
    sign_type_fmt = '<I'
    sign_type_size = struct.calcsize(sign_type_fmt)
    if int(values['--chip'], 0) == 0x18:
        sign_type_offset = 388
        GSHV = '47534856'
        signtype_nvidia = [3, 4] # 3 is for RSA and 4 for ECC
    else:
        GSHV = '4e564441'

    with open(file_path, 'rb') as f:
        header_magic = struct.unpack(header_magic_fmt, f.read(header_magic_size))[0]
        f.seek(0, 0)
        if int(values['--chip'], 0) == 0x18:
            f.seek(sign_type_offset, 0)
            sign_type = struct.unpack(sign_type_fmt, f.read(sign_type_size))[0]
            info_print('sign_type   : %d' % sign_type)

    # Convert decimal to hex
    header_magic = format(header_magic, 'x')
    info_print('header_magic: %s' % header_magic)

    if int(values['--chip'], 0) == 0x18:
        if (header_magic != GSHV) or (sign_type in signtype_nvidia):
            return False
    else :
        if (header_magic != GSHV):
            return False

    return True

class tegraflash_exception(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

def tegraflash_os_path(path):
    newpath = path
    newpath = os.path.expanduser(newpath)
    newpath = os.path.normpath(newpath)

    # convert cygwin path to windows path
    if sys.platform == 'cygwin':
        process = subprocess.Popen(['cygpath', '-w', newpath], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if process.wait() != 0:
            raise tegraflash_exception("Path conversion failed " + newpath)
        newpath = process.communicate()[0]

    newpath = newpath.rstrip('\n')

    if sys.platform == 'win32' or sys.platform == 'cygwin':
        newpath = newpath.replace('/', '\\')

    return newpath

def tegraflash_abs_path(file_path):
    new_path = file_path
    new_path = os.path.expanduser(new_path)

    if not os.path.isabs(new_path):
        new_path = os.path.join(paths['WD'], new_path)

    new_path = tegraflash_os_path(new_path)

    return new_path

def info_print(string):
    diff_time = time.time() - start_time
    print('[ %8.4f ] %s' % (diff_time, string))

def print_process(process, capture_log = False) :
    print_time = True
    diff_time = time.time() - start_time
    log = ''

    while process.poll() is None:
        output = process.stdout.read(1)
        if capture_log:
            log += str(output)
        outputchar = output.decode('ascii')
        if outputchar == '\n' :
            diff_time = time.time() - start_time
            print_time = True
        elif outputchar == '\r' :
            print_time = True
        elif outputchar:
            if print_time:
                print('[ %8.4f ] ' % diff_time, end="")
                print_time = False

        sys.stdout.write(outputchar)
        sys.stdout.flush()

    for string in process.communicate()[0].decode('utf-8').split('\n'):
        if print_time:
            diff_time = time.time() - start_time
            print('[ %8.4f ] ' % diff_time, end='')

        if capture_log:
            log += str(string)
        print(string)
        print_time = True

    return log

def run_command(cmd, enable_print=True):
    log = ''
    if enable_print == True:
        info_print(' '.join(cmd))

    use_shell = False
    if sys.platform == 'win32':
        use_shell = True

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=use_shell, env=cmd_environ)

    if enable_print == True:
        log = print_process(process, enable_print)
    return_code = process.wait()


    if return_code != 0:
        raise tegraflash_exception('Return value ' + str(return_code) +
                '\nCommand ' + ' '.join(cmd))
    return log

def tegraflash_mkdevimages(args, cmd_args):
    global start_time
    start_time = time.time()
    values.update(args)

    if values['--cfg'] is None:
        print('Error: Partition configuration is not specified')
        return 1

    if values['--chip'] is None:
        print('Error: chip is not specified')
        return 1

    tegraflash_get_key_mode()
    tegraflash_parse_partitionlayout()
    tegraflash_sign_images()
    tegraflash_generate_bct()
    tegraflash_update_images()
    tegraflash_generate_devimages(cmd_args)
    info_print('Storage images generated\n')

def getPart_name_by_type(cfg_file, part_type):
    partitions = []
    with open(cfg_file, 'r') as file:
        xml_tree = ElementTree.parse(file)

    root = xml_tree.getroot()

    for node in root.findall('.//partition'):
        if node.get('type') == part_type:
            partitions.extend([node.get('name')])

    return partitions

def tegraflash_flash(args):
    global start_time
    start_time = time.time()
    values.update(args)

    if values['--bl'] is None:
        print('Error: Command line bootloader is not specified')
        return 1

    if values['--cfg'] is None:
        print('Error: Partition configuration is not specified')
        return 1

    if values['--chip'] is None:
        print('Error: chip is not specified')
        return 1

    tegraflash_get_key_mode()
    tegraflash_generate_rcm_message()
    tegraflash_parse_partitionlayout()
    tegraflash_sign_images()
    tegraflash_generate_bct()
    tegraflash_update_images()
    tegraflash_update_bfs_images()
    tegraflash_send_tboot(tegrarcm_values['--signed_list'])
    args['--skipuid'] = False
    tegraflash_send_bct()
    tegraflash_send_bootloader()
    tegraflash_boot('recovery')
    tegraflash_get_storage_info()
    tegraflash_flash_partitions(values['--skipsanitize'])
    tegraflash_flash_bct()
    info_print('Flashing completed\n')

def tegraflash_rcmbl(args):
    global start_time
    start_time = time.time()
    values.update(args)

    if values['--chip'] is None:
        print('Error: chip is not specified')
        return 1

    if values['--applet'] is None:
        print('Error: applet is not specified')
        return 1

    if values['--bct'] is None:
        print('Error: BCT is not specified')
        return 1

    if values['--bldtb'] is None:
        print('Error: Bootloader DTB is not specified')
        return 1

    if values['--applet-cpu'] is None:
        print('Error: CPU-side pre-bootloader binary is not specified')
        return 1

    if values['--bl'] is None:
        print('Error: Command line bootloader is not specified')
        return 1

    if values['--securedev']:
        tegrabct_values['--bct'] = values['--bct']
        tegrabct_values['--rcm_bct'] = values['--rcm_bct']
        tegraflash_send_tboot(args['--applet'])
    else:
        tegraflash_generate_rcm_message()
        tegraflash_parse_partitionlayout()
        tegraflash_sign_images()
        tegraflash_generate_bct()
        tegraflash_update_images()
        tegraflash_send_tboot(tegrarcm_values['--signed_list'])
    args['--skipuid'] = False
    tegraflash_send_bct()
    tegraflash_send_bootimages()
    tegraflash_send_bootloader()
    tegraflash_boot('recovery')
    info_print('RCM-bl started\n')

def tegraflash_rcmboot(args):
    global start_time
    start_time = time.time()
    values.update(args)


    if values['--bl'] is None:
        print('Error: Command line bootloader is not specified')
        return 1

    if values['--chip'] is None:
        print('Error: chip is not specified')
        return 1

    if not values['--tegraflash_v2']:
        if values['--bldtb'] is None:
            print('Error: bl dtb is not specified')
            return 1

        if values['--kerneldtb'] is None:
            print('Error: kernel dtb is not specified')
            return 1

    if values['--securedev']:
        if values['--bct'] is None:
            print('Error: BCT is not specified')
            return 1
        info_print('rcm boot with presigned binaries')
        tegrabct_values['--bct'] = values['--bct']
        tegrabct_values['--rcm_bct'] = values['--rcm_bct']
        tegrabct_values['--mb1_bct'] = values['--mb1_bct']
        tegrabct_values['--membct_rcm'] = values['--mem_bct']

        tegraflash_send_tboot(args['--applet'])
        args['--skipuid'] = False
        tegraflash_send_bct()
        if not values['--tegraflash_v2']:
            tegraflash_send_bootimages()
        tegraflash_send_bootloader(False)
        tegraflash_boot('rcm')
    else:
        tegraflash_get_key_mode()
        tegraflash_generate_rcm_message()
        tegraflash_generate_bct()
        tegraflash_send_tboot(tegrarcm_values['--signed_list'])
        args['--skipuid'] = False
        tegraflash_send_bct()
        tegraflash_send_bootloader()
        tegraflash_boot('rcm')

    info_print('RCM-boot started\n')

def tegraflash_secureflash(args):
    values.update(args)
    tegrabct_values['--bct'] = values['--bct']
    tegrabct_values['--bct_cold_boot'] = values['--bct_cold_boot']
    tegrabct_values['--rcm_bct'] = values['--rcm_bct']
    tegrabct_values['--mb1_bct'] = values['--mb1_bct']
    tegrabct_values['--mb1_cold_boot_bct'] = values['--mb1_cold_boot_bct']
    tegrabct_values['--membct_rcm'] = values['--mem_bct']
    tegrabct_values['--membct_cold_boot'] = values['--mem_bct_cold_boot']
    tegraflash_parse_partitionlayout()
    tegraflash_update_bfs_images()
    tegraflash_send_tboot(args['--applet'])
    args['--skipuid'] = False
    tegraflash_send_bct()
    tegraflash_send_bootloader(False)
    tegraflash_boot('recovery')
    tegraflash_get_storage_info()
    tegraflash_flash_partitions(values['--skipsanitize'])
    tegraflash_flash_bct()
    info_print('Flashing completed\n')

def tegraflash_read(args, partition_name, filename):
    values.update(args)

    if int(values['--chip'], 0) != 0x19 and values['--bl'] is None:
        print('Error: Command line bootloader is not specified')
        return 1

    if values['--securedev']:
        tegrabct_values['--bct'] = values['--bct']
        tegrabct_values['--rcm_bct'] = values['--rcm_bct']
        if values['--cfg'] is not None:
            tegraflash_parse_partitionlayout()
        tegraflash_send_tboot(args['--applet'])
        args['--skipuid'] = False
        if values['--bct'] is not None:
            tegraflash_send_bct()
        tegraflash_get_storage_info()

    else:
        if int(values['--chip'], 0) == 0x19 and values['--sdram_config'] is None:
            tegraflash_generate_rcm_message(True)
        else:
            tegraflash_generate_rcm_message()
        tegraflash_send_tboot(tegrarcm_values['--signed_list'])
        args['--skipuid'] = False

        if values['--tegraflash_v2']:
            tegraflash_get_key_mode()

        if values['--cfg'] is not None:
            tegraflash_parse_partitionlayout()
            tegraflash_sign_images(False)

        if values['--bct'] is None:
            info_print('Reading BCT from device for further operations')
        else:
            info_print('Send BCT from Host')
            tegraflash_generate_bct()
            tegraflash_send_bct()

        if not values['--tegraflash_v2']:
            tegraflash_get_storage_info()

    if int(values['--chip'], 0) != 0x19:
        if int(values['--chip'], 0) == 0x21 and partition_name == 'NCT' and values['--bct'] is None:
            command = exec_file('tegrarcm')
            command.extend(['--read', partition_name, filename])
            run_command(command)
        else:
            tegraflash_send_bootloader()
            tegraflash_boot('recovery')
            tegraflash_read_partition('tegradevflash', partition_name, filename)
    else:
        if int(values['--chip'], 0) == 0x19 and values['--sdram_config'] is None:
            if check_ismb1():
                tegraflash_boot_mb2_applet()
            if check_ismb2():
                tegraflash_read_partition('tegrarcm', partition_name, filename)
        else:
            if not check_iscpubl():
                tegraflash_send_bootloader()
                tegraflash_boot('recovery')
                tegraflash_poll_applet_bl()
            tegraflash_read_partition('tegradevflash', partition_name, filename)

def tegraflash_signwrite(args, partition_name, file_path):
    filename = file_path
    values.update(args)
    if int(values['--chip'], 0) != 0x21:
        tegraflash_get_key_mode()
    if not _is_header_present(file_path):
        temp_file = os.path.basename(file_path)
        if os.path.exists(temp_file):
            i = 1
            while os.path.exists(str(i) + "_" + temp_file):
               i = i + 1
            temp_file = str(i) + "_" + temp_file
        tegraflash_symlink(file_path, temp_file)
        filename = tegraflas_oem_sign_file(temp_file, '')
    tegraflash_write(args, partition_name, filename);

def tegraflash_write(args, partition_name, filename):
    values.update(args)

    if int(values['--chip'], 0) != 0x19 and values['--bl'] is None:
        print('Error: Command line bootloader is not specified')
        return 1

    if values['--securedev']:
        tegrabct_values['--bct'] = values['--bct']
        tegrabct_values['--rcm_bct'] = values['--rcm_bct']
        tegraflash_send_tboot(args['--applet'])
        args['--skipuid'] = False
        if values['--bct'] is not None:
            tegraflash_send_bct()
    else:
        if int(values['--chip'], 0) == 0x19 and values['--sdram_config'] is None:
            tegraflash_generate_rcm_message(True)
        else:
            tegraflash_generate_rcm_message()

        tegraflash_send_tboot(tegrarcm_values['--signed_list'])
        args['--skipuid'] = False

        if values['--tegraflash_v2']:
            tegraflash_get_key_mode()

        if values['--cfg'] is not None:
            tegraflash_parse_partitionlayout()
            tegraflash_sign_images(False)

        if values['--bct'] is None:
            info_print('Reading BCT from device for further operations')
        else:
            info_print('Send BCT from Host')
            tegraflash_generate_bct()
            tegraflash_update_bfs_images()
            tegraflash_send_bct()

    if int(values['--chip'], 0) == 0x19 and values ['--sdram_config'] is None:
        if check_ismb1():
            tegraflash_boot_mb2_applet()
        if check_ismb2():
            tegraflash_write_partition('tegrarcm', partition_name, filename)
            return

    tegraflash_send_bootloader()
    tegraflash_boot('recovery')
    tegraflash_write_partition('tegradevflash', partition_name, filename)
    if int(values['--chip'], 0) == 0x21:
        tegraflash_ignore_bfs()
        tegraflash_flash_bct()
    tegraflash_get_req_info()

def tegraflash_ccgupdate(args, filename1, filename2):
    values.update(args)

    if values['--bl'] is None:
        print('Error: Command line bootloader is not specified')
        return 1

    if values['--securedev']:
        tegrabct_values['--bct'] = values['--bct']
        tegrabct_values['--rcm_bct'] = values['--rcm_bct']
        tegraflash_send_tboot(args['--applet'])
        args['--skipuid'] = False
    else:
        tegraflash_generate_rcm_message()
        tegraflash_send_tboot(tegrarcm_values['--signed_list'])
        args['--skipuid'] = False

        if values['--tegraflash_v2']:
            tegraflash_get_key_mode()

        if values['--cfg'] is not None:
            tegraflash_parse_partitionlayout()
            tegraflash_sign_images(False)

        if values['--bct'] is None:
            info_print('Reading BCT from device for further operations')
        else:
            info_print('Send BCT from Host')
            tegraflash_generate_bct()
            tegraflash_send_bct()

    tegraflash_send_bootloader()
    tegraflash_boot('recovery')
    tegraflash_ccg_update_fw(filename1, filename2)

def tegraflash_get_req_info():
    try:
        if track_py_file is True:
            print('Tracking')
            uidline = uidlog.split('\n')
            uidlineparts = uidline[0].split(':')
            localuid = uidlineparts[1].lstrip().rstrip()
            tnlpath = track.tnspec_get_path(localuid)
            usrname = track.tnspec_get_username()
            pn = track.tnspec_get_platform_1()
            tnbin = track.tnspec_get_tnspec_bin()
            if os.path.isfile(tnlpath):
                if track_py_file is not None:
                    track.track_board_partition_update(tnlpath)
    except:
        info_print('PY file issue')

def tegraflash_erase(args, partition_name):
    values.update(args)

    if values['--bl'] is None:
        print('Error: Command line bootloader is not specified')
        return 1

    if values['--securedev']:
        tegrabct_values['--bct'] = values['--bct']
        tegrabct_values['--rcm_bct'] = values['--rcm_bct']
        tegraflash_send_tboot(args['--applet'])
        args['--skipuid'] = False
        if values['--bct'] is not None:
            tegraflash_send_bct()
    else:
        tegraflash_generate_rcm_message()
        tegraflash_send_tboot(tegrarcm_values['--signed_list'])
        args['--skipuid'] = False

        if values['--tegraflash_v2']:
            tegraflash_get_key_mode()

        if values['--cfg'] is not None:
            tegraflash_parse_partitionlayout()
            tegraflash_sign_images(False)

        if values['--bct'] is None:
            info_print('Reading BCT from device for further operations')
        else:
            info_print('Send BCT from Host')
            tegraflash_generate_bct()
            tegraflash_update_bfs_images()
            tegraflash_send_bct()

    tegraflash_send_bootloader()
    tegraflash_boot('recovery')
    tegraflash_erase_partition(partition_name)

def tegraflash_setverify(args, partition_name):
    values.update(args)

    if values['--bl'] is None:
        raise tegraflash_exception("Command line bootloader not specified")

    if values['--securedev']:
        tegrabct_values['--bct'] = values['--bct']
        tegraflash_send_tboot(args['--applet'])
        args['--skipuid'] = False
    else:
        tegraflash_generate_rcm_message()
        tegraflash_send_tboot(tegrarcm_values['--signed_list'])
        args['--skipuid'] = False

        if values['--tegraflash_v2']:
            tegraflash_get_key_mode()

        if values['--cfg'] is not None:
            tegraflash_parse_partitionlayout()
            tegraflash_sign_images()

        if values['--bct'] is None:
            info_print('Reading BCT from device for further operations')
        else:
            info_print('Send BCT from Host')
            tegraflash_generate_bct()
            tegraflash_send_bct()

    tegraflash_send_bootloader()
    tegraflash_boot('recovery')
    tegraflash_setverify_partition(partition_name)

def tegraflash_test(args, test_args):
    values.update(args)

    if values['--securedev']:
        tegraflash_send_tboot(args['--applet'])
    else:
        tegraflash_generate_rcm_message()
        tegraflash_send_tboot(tegrarcm_values['--signed_list'])

    args['--skipuid'] = False

    if test_args[0] == 'sdram':
        tegraflash_verify_sdram(test_args[1:])
    elif test_args[0] == 'emmc':
        if int(values['--chip'], 0) != 0x21:
            raise tegraflash_exception(test_args[0] + " is not supported")
        tegraflash_verify_emmc(test_args[1:])
    elif test_args[0] == 'eeprom':
        tegraflash_verify_eeprom(test_args[1:])
    else:
        raise tegraflash_exception(test_args[0] + " is not supported")

def tegraflash_parse(args, parse_args):
    values.update(args)

    if parse_args[0] == 'fusebypass':
        tegraflash_parse_fuse_bypass(parse_args[1:])
        if values['--skipuid'] == False:
            args['--skipuid'] = False
    else:
        raise tegraflash_exception(parse_args[0] + " is not supported")

def tegraflash_get_key_mode():
    command = exec_file('tegrasign')
    command.extend(['--key'] + values['--key'])
    command.extend(['--getmode', 'mode.txt'])
    run_command(command)

    with open('mode.txt') as mode_file:
        tegrasign_values['--mode'] = mode_file.read()

def tegraflash_parse_fuse_bypass(fb_args):
    auto = False
    forcebypass = False

    if len(fb_args) < 2:
        raise tegraflash_exception("Invalid arguments")

    auto = (fb_args[1] == 'auto')

    filename = os.path.basename(fb_args[0])
    if not os.path.isfile(paths['TMP'] + '/' + filename):
        tegraflash_symlink(tegraflash_abs_path(fb_args[0]), paths['TMP'] + '/' + filename)
        fb_args[0] = filename

    command = exec_file('tegraparser')
    command.extend(['--fuseconfig', fb_args[0]])
    command.extend(['--sku', fb_args[1]])

    if len(fb_args) == 3:
        if fb_args[2] != 'forcebypass':
            raise tegraflash_exception('Invalid ' + fb_args[2])

        command.extend([fb_args[2]])
        forcebypass = True

    # chip-info is required only for t21x
    if int(values['--chip'], 0) != 0x21:
       forcebypass = True

    if auto or not forcebypass:
        tegraflash_generate_rcm_message()
        tegraflash_send_tboot(tegrarcm_values['--signed_list'])
        values['--skipuid'] = False
        tegraflash_fetch_chip_info()
        command.extend(['--chipinfo', tegrarcm_values['--chip_info']])

    if auto:
        tegraflash_fetch_board_info()
        command.extend(['--boardinfo', tegrarcm_values['--board_info']])

    info_print('Parsing fuse bypass information')
    run_command(command)

def tegraflash_encrypt_sign_binary(exports, args):
    values.update(exports)
    partition_type = "data"
    magicid = ""

    info_print('Generating signature')
    file_path = tegraflash_abs_path(args[0])
    if len(args) == 2:
        partition_type = args[1]

    if int(values['--chip'], 0) == 0x21:
        raise tegraflash_exception("Not supported")

    tegraflash_get_key_mode()
    if not _is_header_present(file_path):
        if int(values['--chip'], 0) == 0x19:
            magicid = tegraflash_get_magicid(partition_type)

        temp_file = os.path.basename(file_path)
        i = 1
        while os.path.exists(str(i) + "_" + temp_file):
            i = i + 1
        temp_file = str(i) + "_" + temp_file
        tegraflash_symlink(file_path, temp_file)
        if values['--encrypt_key'] is not None:
            info_print('Encrypting file')
            signed_file = tegraflash_oem_encrypt_and_sign_file(temp_file, True, magicid)
            filename = tegraflash_oem_encrypt_and_sign_file(signed_file, False, magicid)
        else:
            filename = tegraflas_oem_sign_file(temp_file, magicid)
        temp = filename.split("_", 1)
        new_filename = temp[1]
        if os.path.exists(new_filename):
            os.remove(new_filename)
        tegraflash_symlink(filename, new_filename)
        out_file = paths['WD'] + "/" + new_filename
        if not os.path.isfile(out_file) or not os.path.samefile(new_filename, out_file):
            shutil.copyfile(new_filename, paths['WD'] + "/" + new_filename)
        if values['--encrypt_key'] is not None:
            info_print("Signed and encrypted file: " + paths['WD'] + "/" + new_filename)
        else:
            info_print("Signed file: " + paths['WD'] + "/" + new_filename)

def tegraflash_t19x_encrypt_and_sign(cfg_file):
    test_cfg = 'output.xml'
    signed_files = [ ]
    output_dir = tegraflash_abs_path('encrypted_signed_t19x')

    info_print('Parsing partition layout')
    command = exec_file('tegraparser')
    command.extend(['--pt', values['--cfg']])
    tegraparser_values['--pt'] = os.path.splitext(values['--cfg'])[0] + '.bin'
    run_command(command)

    info_print('Creating list of images to be signed')
    command = exec_file('tegrahost')
    command.extend(['--chip', values['--chip']])
    command.extend(['--partitionlayout', tegraparser_values['--pt']]);
    command.extend(['--list', tegrahost_values['--list']])
    run_command(command)

    if values['--tegraflash_v2']:
         mode = tegrasign_values['--mode']
    mode = 'oem-rsa-sbk'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    command = exec_file('tegrasign')
    command.extend(['--key'] + values['--key'])
    command.extend(['--list', tegrahost_values['--list']])
    command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])
    run_command(command)

    tegraflash_fill_mb1_storage_info()
    with open(tegrahost_values['--list'], 'rt') as file:
         xml_tree = ElementTree.parse(file)
         mode = xml_tree.getroot().get('mode')
         if mode == "pkc":
             list_text = "signed_file"
         else:
             list_text = "encrypt_file"
         for file_nodes in xml_tree.iter('file'):
             file_name = file_nodes.get('name')
             file_type = file_nodes.get('type')
             magic_id = tegraflash_get_magicid(file_type)
             signed_file = tegraflash_oem_encrypt_and_sign_file(file_name, True, magic_id)
             signed_file = tegraflash_oem_encrypt_and_sign_file(signed_file, False, magic_id)
             shutil.copyfile(signed_file, output_dir + "/" + os.path.basename(signed_file))
             file_name = file_name.replace('_sigheader.bin', '.bin')
             file_name = file_name.replace('_sigheader.dtb', '.dtb')
             file_name = file_name.replace('_sigheader.img', '.img')
             file_name = file_name.replace('_sigheader.dat', '.dat')
             signed_files.extend([file_name, signed_file])

         tegraflash_update_enc_cfg_file(signed_files, cfg_file, test_cfg)
         shutil.copyfile(test_cfg, output_dir + "/" + os.path.basename(test_cfg))
         values['--cfg'] = test_cfg

def tegraflash_encrypt_and_sign(exports):
    if int(exports['--chip'], 0) == 0x21:
        tegraflash_sign(exports)
        return

    values.update(exports)
    cfg_file = values['--cfg']
    temp_cfg_file = 'test.xml'
    signed_files = [ ]

    tegraflash_get_key_mode()

    output_dir = tegraflash_abs_path('encrypted_signed')
    images_to_sign = ['mb2_bootloader']
    binaries = []
    tegraflash_generate_rcm_message()

    if values['--cfg'] is not None :
        if int(values['--chip'], 0) == 0x19:
            output_dir = tegraflash_abs_path('encrypted_signed_t19x')
            tegraflash_t19x_encrypt_and_sign(values['--cfg'])
        else:
            tegraflash_parse_partitionlayout()
            tegraflash_encrypt_images(False)
            tegraflash_generate_bct()
            tegraflash_fill_mb1_storage_info()
            tegraflash_parse_partitionlayout()
            tegraflash_encrypt_images(False)
            tegraflash_update_images()

    if values['--bins'] is not None:
        bins = values['--bins'].split(';')
        for binary in bins:
            binary = binary.strip(' ')
            binary = binary.replace('  ', ' ')
            tags = binary.split(' ')
            if (len(tags) < 2):
                raise tegraflash_exception('invalid format ' + binary)

            if tags[0] in images_to_sign:
                magic_id = tegraflash_get_magicid(tags[0])
                tags[1] = tegraflash_oem_encrypt_and_sign_file(tags[1], True, magic_id);
                tags[1] = tegraflash_oem_encrypt_and_sign_file(tags[1], False,magic_id);

            binaries.extend([tags[1]])

    if values['--tegraflash_v2'] and values['--bl']:
        values['--bl'] = tegraflash_oem_encrypt_and_sign_file(values['--bl'], True,'CPBL')
        values['--bl'] = tegraflash_oem_encrypt_and_sign_file(values['--bl'], False,'CPBL')
        binaries.extend([values['--bl']])

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    info_print("Copying signed file in " + output_dir)
    signed_files.extend(tegraflash_copy_signed_binaries(tegrarcm_values['--signed_list'], output_dir))

    if values['--cfg'] is not None and  int(values['--chip'], 0) != 0x19:
        signed_files.extend(tegraflash_encrypt_and_copy_signed_binaries(tegrahost_values['--signed_list'], output_dir))
        tegraflash_update_cfg_file(signed_files, cfg_file, output_dir)
        tegraflash_update_enc_cfg_file(signed_files, cfg_file, temp_cfg_file)
        values['--cfg'] = temp_cfg_file
        tegraflash_parse_partitionlayout()
        tegraflash_generate_bct()
        tegraflash_fill_mb1_storage_info()
        tegraflash_encrypt_images(True)
        tegraflash_update_images()
        signed_files.extend(tegraflash_encrypt_and_copy_signed_binaries(tegrahost_values['--signed_list'], output_dir))
        tegraflash_generate_bct()
        tegraflash_update_images()
        tegraflash_update_cfg_file(signed_files, cfg_file, output_dir)
        shutil.copyfile(tegrabct_values['--bct'], output_dir + "/" + tegrabct_values['--bct'])
    else:
        tegraflash_fill_mb1_storage_info()
        tegraflash_generate_bct()
        shutil.copyfile(tegrabct_values['--bct'], output_dir + "/" + tegrabct_values['--bct'])

    if tegrabct_values['--mb1_bct'] is not None:
        shutil.copyfile(tegrabct_values['--mb1_bct'], output_dir + "/" + tegrabct_values['--mb1_bct'])
    if tegrabct_values['--mb1_cold_boot_bct'] is not None:
        shutil.copyfile(tegrabct_values['--mb1_cold_boot_bct'], output_dir + "/" + tegrabct_values['--mb1_cold_boot_bct'])

    if tegrabct_values['--membct_rcm'] is not None:
        shutil.copyfile(tegrabct_values['--membct_rcm'], output_dir + "/" + tegrabct_values['--membct_rcm'])
    if tegrabct_values['--membct_cold_boot'] is not None:
        shutil.copyfile(tegrabct_values['--membct_cold_boot'], output_dir + "/" + tegrabct_values['--membct_cold_boot'])
    for signed_binary in binaries:
        info_print(signed_binary)
        shutil.copyfile(signed_binary, output_dir + "/" + signed_binary)

    if os.path.isfile('mb1_t194_dev_sigheader.bin.encrypt'):
        mb1_file = tegraflash_oem_encrypt_and_sign_file('mb1_t194_dev_sigheader.bin.encrypt', False, "MB1B")
        shutil.copyfile(mb1_file, output_dir + "/" + mb1_file )

    if os.path.isfile('mb1_t194_prod_sigheader.bin.encrypt'):
        mb1_file = tegraflash_oem_encrypt_and_sign_file('mb1_t194_prod_sigheader.bin.encrypt', False, "MB1B")
        shutil.copyfile(mb1_file, output_dir + "/" + mb1_file )

    # Generate index file when encrypt and sign images
    if int(values['--chip'], 0) == 0x18 or int(values['--chip'], 0) == 0x19:
        command = exec_file('tegraparser')
        command.extend(['--generategpt', '--pt', tegraparser_values['--pt']])
        run_command(command)
        import re
        patt = re.compile(".*(mbr|gpt).*\.bin")
        contents = os.listdir('.')
        for f in contents:
            if patt.match(f):
                shutil.copyfile(f, output_dir + "/" + f)
        # --pt flash.xml.bin --generateflashindex flash.xml.tmp <out>
        flash_index = "flash.idx"
        new_cfg_file = output_dir + "/flash.xml.tmp"
        original_cfg = output_dir + "/" + os.path.basename(values['--cfg'])
        if os.path.exists(original_cfg) and not values['--cfg'].endswith(".tmp"):
            shutil.copyfile(original_cfg, new_cfg_file)
        if os.path.exists(new_cfg_file):
            tegraflash_update_cfg_file(signed_files, new_cfg_file, output_dir, only_generated=True)
            tegraflash_generate_index_file(new_cfg_file, flash_index)
            shutil.copyfile(flash_index, output_dir + "/" + flash_index)
        else:
            info_print("Failed to find flash.xml.tmp. Skip generating flash index file for now.")

def tegraflash_generate_index_file(cfg_file, index_file_location):
    command = exec_file('tegraparser')
    command.extend(['--pt', tegraparser_values['--pt'], \
            '--generateflashindex', cfg_file, \
            index_file_location])
    run_command(command)

def tegraflash_get_magicid(bin_type):
   if bin_type == "mts_preboot":
       return 'MTSP'
   if bin_type == "mts_mce":
       return 'MTSM'
   if bin_type == "mts_proper":
       return 'MTSB'
   if bin_type == "mb2_bootloader":
       return 'MB2B'
   if bin_type == "bootloader_dtb":
       return 'CDTB'
   if bin_type == "spe_fw":
       return 'SPEF'
   if bin_type == "bpmp_fw":
       return 'BPMF'
   if bin_type == "bpmp_fw_dtb":
       return 'BPMD'
   if bin_type == "tlk":
       return 'TOSB'
   if bin_type == 'eks':
      return 'EKSB'
   return 'DATA'

# Core function
def tegraflash_sign():

    cfg_file = values['--cfg']
    signed_files = [ ]

    tegraflash_get_key_mode()

    # Change the path!!
    output_dir = tegraflash_abs_path('signed')
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir, ignore_errors=True)
    os.makedirs(output_dir)

    images_to_sign = ['mts_preboot', 'mts_bootpack', 'mts_mce', 'mts_proper', 'mb2_bootloader', 'fusebypass', 
                    'bootloader_dtb', 'spe_fw', 'bpmp_fw', 'bpmp_fw_dtb', 'tlk', 'eks', 'dtb', 'ebt', 'tbc']
    binaries = []
    tegraflash_generate_rcm_message() 
    tegraflash_parse_partitionlayout()
    tegraflash_sign_images()
    tegraflash_generate_bct() 
    tegraflash_update_images() # Passed
    # tegraflash_update_bfs_images() # COMPLAINING "flash.xml.bin open failed"

    info_print("Copying signed file in " + output_dir)
    signed_files.extend(tegraflash_copy_signed_binaries(tegrarcm_values['--signed_list'], output_dir))

    print("Am I reaching here?")
    
    # only if values['--cfg'] is not None :
    signed_files.extend(tegraflash_copy_signed_binaries(tegrahost_values['--signed_list'], output_dir))
    shutil.copyfile(tegrabct_values['--bct'], output_dir + "/" + tegrabct_values['--bct'])
    if int(values['--chip'], 0) == 0x21 and int(values['--chip_major'], 0) > 1:
        shutil.copyfile(tegrabct_values['--rcm_bct'], output_dir + "/" + tegrabct_values['--rcm_bct'])
    tegraflash_update_cfg_file(signed_files, cfg_file, output_dir, int(values['--chip'], 0))

    for signed_binary in binaries:
        shutil.copyfile(signed_binary, output_dir + "/" + signed_binary)

    if tegraparser_values['--pt'] is not None:
        shutil.copyfile(tegraparser_values['--pt'], output_dir + "/" + tegraparser_values['--pt'])

def tegraflash_update_cfg_file(signed_files, cfg_file, output_dir, chip=None, only_generated=False):
    secondary_gpt_found = None
    signed_files = dict(zip(signed_files[::2], signed_files[1::2]))
    with open(cfg_file, 'r') as file:
        xml_tree = ElementTree.parse(file)

    root = xml_tree.getroot()

    for node in root.findall('.//partition'):
        file_node = node.find('filename')
        part_type = node.attrib.get('type').strip()
        part_name = node.attrib.get('name').strip()
        if file_node is not None and not only_generated:
            file_name = file_node.text.strip()
            if node.get('authentication_group')is not None:
                if node.get('authentication_group') == node.get('id'):
                    file_name = file_name.replace('.bin','_multisigheader.bin')
                    file_name = file_name.replace('.dtb','_multisigheader.dtb')
                    file_name = file_name.replace('.img','_multisigheader.img')
                else:
                    file_name = file_name.replace('.bin','_nosigheader.bin')
                    file_name = file_name.replace('.dtb','_nosigheader.dtb')
                    file_name = file_name.replace('.img','_nosigheader.img')
            if (file_name in signed_files and node.get('oem_sign') == "true") \
                    or part_type == "mb1_bootloader" or part_type == "wb0" \
                    or (part_type == "WB0" and chip != 0x21) \
                    or (file_name in signed_files and chip == 0x21):
                file_node.text = " " + signed_files[file_name] + " "
        else:
            # add filename for partitions that have been created and signed
            file_name = None
            if part_name == "BCT":
                file_name = tegrabct_values['--bct']
                if int(values['--chip'], 0) == 0x21 and int(values['--chip_major'], 0) > 1:
                    file_name = tegrabct_values['--rcm_bct']

            if part_name == "MB1_BCT" or part_name == "MB1_BCT_b":
                file_name = tegrabct_values['--mb1_cold_boot_bct'];

            if part_name == "MEM_BCT" or part_name == "MEM_BCT_b":
                file_name = tegrabct_values['--membct_cold_boot']

            if part_name == "secondary_gpt" \
                    or part_name == "master_boot_record" \
                    or part_name == "primary_gpt" :
                for device in root.findall('.//device'):
                    if device.attrib.get('type').strip() == "sdmmc_boot" \
                            and device.attrib.get('instance').strip() == "3" :
                        if part_name == "secondary_gpt" \
                                and secondary_gpt_found is None:
                            file_name = "gpt_secondary_0_3.bin"
                            secondary_gpt_found = "true";
                            break;
                    if device.attrib.get('type').strip() == "spi" \
                            and device.attrib.get('instance').strip() == "0" :
                        if part_name == "secondary_gpt" \
                                and secondary_gpt_found is None:
                            file_name = "gpt_secondary_3_0.bin"
                            secondary_gpt_found = "true";
                            break;
                    if device.attrib.get('type').strip() == "sdmmc_user" \
                            and device.attrib.get('instance').strip() == "3" :
                        if part_name == "master_boot_record" :
                            file_name = "mbr_1_3.bin"
                        if part_name == "primary_gpt" :
                            file_name = "gpt_primary_1_3.bin"
                        if part_name == "secondary_gpt" :
                            file_name = "gpt_secondary_1_3.bin"
                    if device.attrib.get('type').strip() == "nvme" \
                            and device.attrib.get('instance').strip() == "0" :
                        if part_name == "master_boot_record" :
                            file_name = "mbr_9_0.bin"
                        if part_name == "primary_gpt" :
                            file_name = "gpt_primary_9_0.bin"
                        if part_name == "secondary_gpt" :
                            file_name = "gpt_secondary_9_0.bin"
                    if device.attrib.get('type').strip() == "sdcard" \
                            and device.attrib.get('instance').strip() == "0" :
                        if part_name == "master_boot_record" :
                            file_name = "mbr_6_0.bin"
                        if part_name == "primary_gpt" :
                            file_name = "gpt_primary_6_0.bin"
                        if part_name == "secondary_gpt" :
                            file_name = "gpt_secondary_6_0.bin"

            if file_name is not None:
                new_tag = ElementTree.SubElement(node, 'filename')
                new_tag.text = " " + file_name + " "

    if chip == 0x21:
        cfg_file = cfg_file.replace(".tmp", "")
    with open (output_dir + "/" + os.path.basename(cfg_file), 'wb+') as file:
        file.write(ElementTree.tostring(root))

def tegraflash_update_enc_cfg_file(signed_files, cfg_file, temp_cfg_file):
    signed_files = dict(zip(signed_files[::2], signed_files[1::2]))
    with open(cfg_file, 'r') as file:
        xml_tree = ElementTree.parse(file)

    root = xml_tree.getroot()

    for node in root.findall('.//filename'):
        file_name = node.text.strip()
        if file_name in signed_files:
            node.text = " " + signed_files[file_name] + " "

    with open (temp_cfg_file, 'wb+') as file:
        file.write(ElementTree.tostring(root))

def tegraflash_encrypt_and_copy_signed_binaries(xml_file, output_dir):
    signed_files = [ ]
    with open(xml_file, 'rt') as file:
        xml_tree = ElementTree.parse(file)

    mode = xml_tree.getroot().get('mode')
    if mode == "pkc":
        list_text = "signed_file"
    else:
        list_text = "encrypt_file"

    for file_nodes in xml_tree.iter('file'):
        file_name = file_nodes.get('name')
        file_type = file_nodes.get('type')
        signed_file = file_nodes.find(mode).get(list_text)
        magic_id = tegraflash_get_magicid(file_type)
        if file_type != "mb1_bootloader" and file_type != "wb0":
            signed_file = tegraflash_oem_encrypt_and_sign_file(signed_file, False, magic_id)
        shutil.copyfile(signed_file, output_dir + "/" + os.path.basename(signed_file))
        if int(values['--chip'], 0) == 0x18:
            file_name = file_name.replace('_sigheader', '')
            file_name = file_name.replace('_wbheader.bin.encrypt', '.bin')
            file_name = file_name.replace('_wbheader', '')
        if int(values['--chip'], 0) == 0x19:
            file_name = file_name.replace('_sigheader', '')
            file_name = file_name.replace('_wbheader.bin.encrypt', '.bin')
            file_name = file_name.replace('_wbheader', '')
            file_name = file_name.replace('dev.bin', 'dev_sigheader.bin')
            file_name = file_name.replace('_sigheader.encrypt', '')
        signed_files.extend([file_name, signed_file])
    return signed_files

def tegraflash_copy_signed_binaries(xml_file, output_dir):
    signed_files = [ ]
    with open(xml_file, 'rt') as file:
        xml_tree = ElementTree.parse(file)

    mode = xml_tree.getroot().get('mode')
    if mode == "pkc":
        list_text = "signed_file"
    else:
        if mode == "ec" or mode == "eddsa":
            list_text = "signed_file"
        else:
            list_text = "encrypt_file"

    for file_nodes in xml_tree.iter('file'):
        file_name = file_nodes.get('name')
        signed_file = file_nodes.find(mode).get(list_text)
        shutil.copyfile(signed_file, output_dir + "/" + os.path.basename(signed_file))
        if int(values['--chip'], 0) != 0x21:
            file_name = file_name.replace('_sigheader', '')
            file_name = file_name.replace('_wbheader', '')
        signed_files.extend([file_name, signed_file])

    return signed_files

def tegraflash_boot(boot_type):
    command = exec_file('tegrarcm')
    command.extend(['--boot', boot_type])
    run_command(command)
    if boot_type == 'recovery':
        tegraflash_poll_applet_bl()

def tegraflash_fetch_board_info():
    info_print('Retrieving board information')
    command = exec_file('tegrarcm')
    command.extend(['--oem', 'platformdetails', 'eeprom', tegrarcm_values['--board_info']])
    run_command(command)

def tegraflash_fetch_chip_info():
    info_print('Retrieving board information')
    command = exec_file('tegrarcm')
    command.extend(['--oem', 'platformdetails', 'chip', tegrarcm_values['--chip_info']])
    try:
        run_command(command)
    except tegraflash_exception as e:
        command[0] = exec_file('tegradevflash')[0]
        run_command(command)

def tegraflash_dump(args, dump_args):
    values.update(args)
    if dump_args[0] == 'ram' and int(values['--chip'], 0) == 0x18:
            tegraflash_dumpram_t18x(dump_args[1:])
            return

    is_pdf = (dump_args[0] == 'eeprom')

    if values['--securedev']:
        tegrabct_values['--bct'] = values['--bct']
        tegrabct_values['--rcm_bct'] = values['--rcm_bct']
        tegraflash_send_tboot(args['--applet'])
        tegraflash_send_bct()
    else:
        tegraflash_generate_rcm_message(is_pdf)
        tegraflash_send_tboot(tegrarcm_values['--signed_list'])
    args['--skipuid'] = False

    if dump_args[0] == 'ram':
        tegraflash_dumpram(values, dump_args[1:])
    elif dump_args[0] == 'ptm':
        if int(values['--chip'], 0) == 0x18:
            raise tegraflash_exception(dump_args[0] + " is not supported")
        tegraflash_dumpptm(dump_args[1:])
    elif dump_args[0] == 'eeprom':
        tegraflash_dumpeeprom(args, dump_args[1:])
    elif dump_args[0] == 'custinfo':
        if int(values['--chip'], 0) == 0x18 or int(values['--chip'], 0) == 0x19:
            raise tegraflash_exception(dump_args[0] + " is not supported")
        tegraflash_read(args, 'bct', 'tmp.bct')
        tegraflash_dumpcustinfo(dump_args[1:])
    elif dump_args[0] == 'bit':
        if int(values['--chip'], 0) == 0x18 or int(values['--chip'], 0) == 0x19:
            command = exec_file('tegrarcm')
            command.extend(['--oem', 'dump', dump_args[0], dump_args[1]])
            run_command(command)
        else:
            raise tegraflash_exception(dump_args[0] + " is not supported")
    elif dump_args[0] == 'bct':
        if int(values['--chip'], 0) == 0x18:
            command = exec_file('tegrarcm')
            command.extend(['--oem', 'dump', dump_args[0], dump_args[1]])
            run_command(command)
        else:
            raise tegraflash_exception(dump_args[0] + " is not supported")
    else:
        raise tegraflash_exception(dump_args[0] + " is not supported")

def tegraflash_dumpeeprom(args, params):
    values.update(args)
    is_tegrarcm_command = False;

    if int(values['--chip'], 0) == 0x21:
        info_print('dump EEPROM info')
        command = exec_file('tegrarcm')

        if len(params) > 1:
            out_file = params[1]
        else:
            out_file = 'cvm.bin'

        out_file = tegraflash_abs_path(out_file)
        command.extend(['--oem', 'platformdetails', 'eeprom', out_file])
        run_command(command)
        command = exec_file('tegrarcm')
        command.extend(['--reboot', 'recovery'])
        run_command(command)
        time.sleep(2)
        return

    if len(params) == 0:
        print("Error: EEPROM module not specified")
        return

    if args['--bl'] is not None:
        tegraflash_get_key_mode()
        tegraflash_generate_bct()
        tegraflash_send_bct()
        tegraflash_send_bootloader()
        tegraflash_boot('recovery')
        command = exec_file('tegradevflash')
    else:
        if int(values['--chip'], 0) == 0x19 and not check_ismb2():
            tegraflash_boot_mb2_applet()

        command = exec_file('tegrarcm')
        is_tegrarcm_command = True

    if int(values['--chip'], 0) == 0x19:
        tegraflash_fetch_chip_info()
        out_file = tegraflash_abs_path(tegrarcm_values['--chip_info'] + '_bak')
        shutil.copyfile(tegrarcm_values['--chip_info'], out_file)

    info_print('Retrieving EEPROM data')
    out_file = tegraflash_abs_path(tegrarcm_values['--board_info'])
    try:
        eeprom_module = tegraflash_eeprom_name_map[ values['--chip'] ][ params[0] ]
    except KeyError:
        raise tegraflash_exception('eeprom module %s not recognized for %s' % (params[0], values['--chip']))
    if len(params) > 1:
        out_file = tegraflash_abs_path(params[1])
    command.extend(['--oem', 'platformdetails', 'eeprom', eeprom_module.lower(), out_file])
    try:
        run_command(command)
    except tegraflash_exception as e:
        if is_tegrarcm_command:
            command = exec_file('tegradevflash')
            command.extend(['--oem', 'platformdetails', 'eeprom', eeprom_module.lower(), out_file])
            run_command(command)
        else:
            raise e

def tegraflash_dumpcustinfo(dump_args):
    info_print('Dumping customer Info')
    command = exec_file('tegrabct')
    command.extend(['--bct', 'tmp.bct'])
    command.extend(['--chip', values['--chip'], values['--chip_major']])
    if len(dump_args) > 0:
        file_path = tegraflash_abs_path(dump_args[0])
    else:
        file_path = tegraflash_abs_path("custinfo.bin")

    command.extend(['--custinfo', file_path])
    run_command(command)

def tegraflash_tboot_reset(args):
    if args[0] == 'coldboot':
        info_print('Coldbooting the device')
    elif args[0] == 'recovery':
        info_print('Rebooting to recovery mode')
    else:
        raise tegraflash_exception(args[0] + " is not supported")

    command = exec_file('tegrarcm')
    command.extend(['--reboot', args[0]])
    run_command(command)
    time.sleep(2)

def tegraflash_dumpram_t18x(dump_args):
    separator = '---------------------------------------------------'
    info_print('Dumping Ram - Checking if requested region is valid')
    info_print(separator)
    command = exec_file('tegrarcm')
    command.extend(['--oem', 'checkdumpramrequest'])
    command.extend([dump_args[0]])
    command.extend([dump_args[1]])
    run_command(command)

    info_print('Dumping Ram')
    info_print(separator)
    command = exec_file('tegrarcm')
    command.extend(['--oem', 'dumpram'])
    command.extend([dump_args[0]])
    command.extend([dump_args[1]])
    file_path = tegraflash_abs_path(dump_args[2])
    command.extend([file_path])
    run_command(command)
    tegraflash_boot('coldboot')

def tegraflash_dumpram(values, dump_args):
    if len(dump_args) < 3:
        raise tegraflash_exception("Ramdump: Invalid parameters!\n"
                "Usage: dump ram <offset> <size> <file_name>")
    if int(dump_args[1], 0) <= 0:
        raise tegraflash_exception("Size(%s) is invalid, must be >0!" % dump_args[1])
    separator = '---------------------------------------------------'
    info_print('Dumping Ram - Checking if requested region is valid')
    info_print(separator)
    command = exec_file('tegrarcm')
    command.extend(['--oem', 'checkdumpramrequest'])
    command.extend([dump_args[0]])
    command.extend([dump_args[1]])
    run_command(command)

    if len(dump_args[0]) > 0 and len(dump_args[1]) > 0 and len(dump_args) > 2:
        boundary = int(dump_args[0], 0) + int(dump_args[1], 0) - 1
        if boundary <= 0xFFFFFFFF:
            info_print('Dumping Ram - Dump region within 2GB Memory boundary')
            info_print(separator)
            command = exec_file('tegrarcm')
            command.extend(['--oem', 'dumpram'])
            command.extend([dump_args[0]])
            command.extend([dump_args[1]])
            file_path = tegraflash_abs_path(dump_args[2])
            command.extend([file_path])
            run_command(command)
            resettype = ['coldboot']
            tegraflash_tboot_reset(resettype)
        elif boundary > 0xFFFFFFFF and int(dump_args[0], 0) <= 0xFFFFFFFF:
            tempfilenames = ['temp1.bin', 'temp2.bin']
            info_print('Dumping Ram - Dump region spanning across 2GB Memory boundary')
            info_print(separator)
            info_print('Saving dump of memory region requested < 2GB')
            command = exec_file('tegrarcm')
            command.extend(['--oem', 'dumpram'])
            command.extend([dump_args[0]])
            memoryleft = 0x100000000 - int(dump_args[0], 0)
            command.extend(['' + hex(memoryleft)])
            file_path = tempfilenames[0]
            command.extend([file_path])
            run_command(command)

            info_print('Loading TBoot-CPU to initialize SMMU')
            tegraflash_dumpram_load_tboot_cpu(values)

            info_print('Saving dump of memory region requested > 2GB')
            command = exec_file('tegrarcm')
            command.extend(['--oem', 'dumpram'])
            command.extend(['0x100000000'])
            memorydumped = 0x100000000 - int(dump_args[0], 0)
            memoryleft = int(dump_args[1], 0) - memorydumped
            command.extend(['' + hex(memoryleft)])
            file_path = tempfilenames[1]
            command.extend([file_path])
            run_command(command)
            resettype = ['coldboot']
            tegraflash_tboot_reset(resettype)
            #merge files by reading 10MB blocks
            blocksize = 10485760
            info_print('Merging temp files into :' + tegraflash_abs_path(dump_args[2]))
            fout = file(tegraflash_abs_path(dump_args[2]),'wb')
            for a in tempfilenames:
                fin = file(a,'rb')
                while True:
                    data = fin.read(blocksize)
                    if not data:
                        break
                    fout.write(data)
                fin.close()
            fout.close()
        else:
            info_print('Dumping Ram - Dump region entirely beyond 2GB Memory boundary')
            info_print(separator)
            info_print('Loading TBoot-CPU to initialize SMMU')

            tegraflash_dumpram_load_tboot_cpu(values)
            info_print('Saving dump of memory > 2GB')
            command = exec_file('tegrarcm')
            command.extend(['--oem', 'dumpram'])
            command.extend([dump_args[0]])
            command.extend([dump_args[1]])
            file_path = tegraflash_abs_path(dump_args[2])
            command.extend([file_path])
            run_command(command)
            resettype = ['coldboot']
            tegraflash_tboot_reset(resettype)

def tegraflash_dumpram_load_tboot_cpu(values):
    info_print('Sending Tboot-CPU')
    command = exec_file('tegrarcm')
    if values['--securedev']:
        if int(values['--chip'], 0) == 0x21 and int(values['--chip_major'], 0) > 1:
            command.extend(['--download', 'tbc', 'nvtboot_cpu_t210b01.bin.signed', '0', '0'])
        else:
            command.extend(['--download', 'tbc', 'nvtboot_cpu.bin.signed', '0', '0'])
    else:
        command.extend(['--download', 'tbc', 'nvtboot_cpu.bin', '0', '0'])
    run_command(command)

def tegraflash_dumpptm(dump_args):
    info_print('Dumping PTM')
    command = exec_file('tegrarcm')
    command.extend(['--oem', 'dumpptm'])

    if len(dump_args) > 0:
        command.extend([dump_args[0]])

    run_command(command)

def tegraflash_fuse_sendbl():
    if values['--securedev']:
        tegrabct_values['--bct'] = values['--bct']
        tegrabct_values['--rcm_bct'] = values['--rcm_bct']
        tegrabct_values['--mb1_bct'] = values['--mb1_bct']
        tegrabct_values['--mb1_cold_boot_bct'] = values['--mb1_cold_boot_bct']
        tegrabct_values['--membct_rcm'] = values['--mem_bct']
        tegrabct_values['--membct_cold_boot'] = values['--mem_bct_cold_boot']
        tegraflash_send_bct()
        tegraflash_send_bootloader(False)
    elif values['--cfg'] is not None:
        tegraflash_get_key_mode()
        tegraflash_parse_partitionlayout()
        tegraflash_sign_images()
        tegraflash_generate_bct()
        tegraflash_update_images()
        tegraflash_send_bct()
        tegraflash_send_bootloader()
    else:
        raise tegraflash_exception("Fuse burning is missing either --securedev or --cfg.")
    tegraflash_boot('recovery')

def tegraflash_burnfuses(args, fuse_args):
    values.update(args)

    info_print('Burning fuses')

    if values['--chip'] is None:
        raise tegraflash_exception("chip is not specified")

    try:
        if values['--securedev']:
            tegraflash_send_tboot(args['--applet'])
        else:
            tegraflash_generate_rcm_message()
            tegraflash_send_tboot(tegrarcm_values['--signed_list'])
    except tegraflash_exception as e:
        info_print('Send tboot failed. Bootrom is likely not running, try to detect whether mb1/mb2/cpubl is running.')
        tegraflash_poll_applet_bl()

    command = exec_file('tegrarcm')
    if len(fuse_args[0]) > 0 :
        command = exec_file('tegrarcm')
        if fuse_args[0] == 'dummy' or fuse_args[0] == 'fskp':
            command.extend(['--oem', 'burnfuses', fuse_args[0] ])
        else:
            filename = os.path.splitext(fuse_args[0])
            if filename[1] != '.xml':
                raise tegraflash_exception("Not an xml file")
            info_print('Parsing fuse info as per xml file')
            command = exec_file('tegraparser')
            command.extend(['--fuse_info', fuse_args[0], tegrarcm_values['--fuse_info']])
            run_command(command)

            command = exec_file('tegrarcm')
            command.extend(['--oem', 'burnfuses'])
            command.extend([tegrarcm_values['--fuse_info']])
    else:
        command = exec_file('tegrarcm')
        command.extend(['--oem', 'burnfuses'])
    try:
        run_command(command)
        if int(values['--chip'], 0) == 0x21:
            resettype = ['recovery']
            tegraflash_tboot_reset(resettype)
        if values['--tegraflash_v2']:
            command = exec_file('tegrarcm')
            command.extend(['--boot', 'recovery'])
            run_command(command)
    except tegraflash_exception as e:
        if values['--tegraflash_v2']:
            info_print('trying fusing with CPU binary')
            command[0] = exec_file('tegradevflash')[0]
            tegraflash_fuse_sendbl()
            run_command(command)

            command = exec_file('tegradevflash')
            command.extend(['--reboot', 'recovery'])
            run_command(command)
        else :
            raise tegraflash_exception("Fuse burning not supported at CPU bl level")

def tegraflash_blowfuses(exports, args):
    values.update(exports)

    if args is None:
        raise tegraflash_exception("Require an argument")

    filename = os.path.splitext(args[0])
    if filename[1] != '.xml':
        raise tegraflash_exception("Not an xml file")

    info_print('Parsing fuse info as per xml file')
    command = exec_file('tegraparser')
    command.extend(['--fuse_info', args[0], tegrarcm_values['--fuse_info']])
    run_command(command)

    if values['--chip'] is None:
        raise tegraflash_exception("chip is not specified")

    if values['--securedev']:
        tegraflash_send_tboot(exports['--applet'])
    else:
        tegraflash_generate_rcm_message()
        tegraflash_send_tboot(tegrarcm_values['--signed_list'])

    info_print('Blowing fuses')

    command = exec_file('tegrarcm')
    command.extend(['--oem', 'blowfuses'])
    command.extend([tegrarcm_values['--fuse_info']])

    run_command(command)

def tegraflash_readfuses(exports, args):
    values.update(exports)

    info_print('Reading fuses')
    try:
        if values['--securedev']:
            tegraflash_send_tboot(exports['--applet'])
        else:
            tegraflash_generate_rcm_message()
            tegraflash_send_tboot(tegrarcm_values['--signed_list'])
    except tegraflash_exception as e:
        info_print('Send tboot failed. Bootrom is likely not running, try to detect whether mb1/mb2/cpubl is running.')
        tegraflash_poll_applet_bl()

    if int(values['--chip'], 0) == 0x21 :
        if not args[0]:
            args[0] = "dut_fuses.bin"
        filename = tegraflash_abs_path(args[0])
        command = exec_file('tegrarcm')
        command.extend(['--oem', 'readfuses', filename])
        run_command(command)

        _parse_fuses(filename)
        resettype = ['recovery']
        tegraflash_tboot_reset(resettype)

    if int(values['--chip'], 0) == 0x18 or int(values['--chip'], 0) == 0x19:
        if len(args) != 2 :
            raise tegraflash_exception("Command requires 2 params")
        filename = tegraflash_abs_path(args[0])
        fusexml = args[1]
        if os.path.splitext(fusexml)[1] != '.xml':
            raise tegraflash_exception("Not an xml file")
        info_print('Parsing fuse info as per xml file')
        command = exec_file('tegraparser')
        command.extend(['--get_fuse_names', fusexml, tegrarcm_values['--get_fuse_names']])
        run_command(command)

        scatter = '__fuse_read_scatter.bin'
        if values['--tegraflash_v2']:
            try:
                f_out = open(filename, 'w')
            except:
                raise tegraflash_exception("Open " + filename + ' failed.')

            info_print('trying to read fuse with CPU binary')
            tegraflash_fuse_sendbl()
            with open(tegrarcm_values['--get_fuse_names']) as f_fuses:
                for fuse in f_fuses:
                    fuse=fuse.rstrip()
                    command = exec_file('tegraparser')
                    command.extend(['--read_fusetype', fuse, tegrarcm_values['--read_fuse']])
                    run_command(command)
                    command = exec_file('tegradevflash')
                    command.extend(['--oem', 'readfuses', scatter, tegrarcm_values['--read_fuse']])
                    run_command(command)
                    f_scatter = open(scatter, 'rb')
                    f_bytes = bytearray(f_scatter.read())
                    # For fuses which their sizes are 4 bytes, convert to big endian here.
                    # (ARM is little endian).
                    if len(f_bytes) == 4:
                        tmp = f_bytes[0]
                        f_bytes[0] = f_bytes[3]
                        f_bytes[3] = tmp
                        tmp = f_bytes[1]
                        f_bytes[1] = f_bytes[2]
                        f_bytes[2] = tmp
                    f_string = ''.join(['%02x' % b for b in f_bytes])
                    f_out.write(fuse + ': ' + f_string + '\n')
                    f_scatter.close()
            f_out.close()
        else :
            raise tegraflash_exception("Fuse reading not supported at CPU bl level")

def tegraflash_provision_rollback(exports, args):
    values.update(exports)

    info_print('Provision Rollback key')

    if values['--chip'] is None:
        print('Error: chip is not specified')
        return 1

    if values['--bct'] is not None:

        if values['--nct'] is None:
            print('Error: NCT file is not specified')
            return 1

        tegraflash_generate_rcm_message()
        tegraflash_generate_bct()
        if values['--securedev']:
            tegraflash_send_tboot(exports['--applet'])
        else:
            tegraflash_send_tboot(tegrarcm_values['--signed_list'])
        tegraflash_send_bct()
        tegraflash_get_storage_info()

    else:
        if values['--securedev']:
            tegraflash_send_tboot(exports['--applet'])
        else:
            tegraflash_generate_rcm_message()
            tegraflash_send_tboot(tegrarcm_values['--signed_list'])

    if values['--tegraflash_v2']:
       if len(args) != 2 :
            raise tegraflash_exception("Command requires 2 params : dummy/fskp and rpmb device type (emmc/ufs)")
       if len(args[0]) > 0 :
           command = exec_file('tegrarcm')
           if args[0] == 'dummy' or args[0] == 'fskp':
               command.extend(['--oem', 'setrollback', args[0], args[1] ])
               run_command(command)
           else:
               filename = os.path.splitext(args[0])
               if filename[1] != '.xml':
                   print('Error: not an xml file')
                   raise tegraflash_exception(args[0] + " is not supported")
               info_print('Parsing fuse info as per xml file')
               command = exec_file('tegraparser')
               command.extend(['--fuse_info', args[0], tegrarcm_values['--fuse_info']])
               run_command(command)

               command = exec_file('tegrarcm')
               command.extend(['--oem', 'setrollback', tegrarcm_values['--fuse_info']])
               run_command(command)
    else:
        # generate rollback key
        command = exec_file('tegrarcm')
        command.extend(['--oem', 'getrollback', tegrarcm_values['--rollback_data']])
        run_command(command)

        # provision rollback key
        tegraflash_send_bootloader()
        tegraflash_boot('recovery')
        command = exec_file('tegradevflash')
        command.extend(['--oem', 'setrollback', tegrarcm_values['--rollback_data']])
        run_command(command)

def tegraflash_verify_sdram(test_args):
    if values['--bct'] is not None:
        tegraflash_generate_bct()
        tegraflash_send_bct()

    info_print('Verifying SDRAM')
    command = exec_file('tegrarcm')
    command.extend(['--oem', 'verifysdram'])
    command.extend(test_args)
    run_command(command)

def tegraflash_symlink(srcfile, destfile):
    srcfile = tegraflash_os_path(srcfile)
    destfile = tegraflash_os_path(destfile)

    if sys.platform == 'win32' or sys.platform == 'cygwin':
        process = subprocess.Popen(['cmd', '/c', 'mklink /H ' + destfile + ' ' + srcfile], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        process.wait();
    else:
        os.symlink(srcfile, destfile)

def tegraflash_nvsign(exports, in_file, only_sign):
    values.update(exports)

    if int(values['--chip'], 0) not in [0x19, 0x23]:
        return
    filename = os.path.basename(in_file)
    info_print(filename)
    out_file = os.path.splitext(filename)[0] + '_dev' + os.path.splitext(filename)[1]
    mode = tegrasign_values['--mode']
    command = exec_file('tegrahost')
    command.extend(['--chip', values['--chip']])
    command.extend(['--align', in_file])
    run_command(command)

    if not os.path.exists(filename):
        tegraflash_symlink(in_file, filename)

    if not _is_header_present(in_file):
        # check if encryption skip is set
        if bool(only_sign) == False:
            command = exec_file('tegrasign')
            command.extend(['--key', values['--nvencrypt_key']])
            command.extend(['--file', filename])
            run_command(command)
            filename = os.path.splitext(filename)[0] + '_encrypt' + os.path.splitext(filename)[1]

        mode = 'nvidia-rsa'
        command = exec_file('tegrahost')
        command.extend(['--chip', values['--chip'], values['--chip_major']])
        command.extend(['--magicid', 'MB1B'])
        command.extend(['--addmb1nvheader', filename, mode])
        run_command(command)
        filename = os.path.splitext(filename)[0] + '_sigheader' + os.path.splitext(filename)[1]

    command = exec_file('tegrasign')
    command.extend(['--key', values['--nv_key']])
    if int(values['--cl'],0) >= 39027124:
        command.extend(['--offset', '3792'])
        command.extend(['--length', '304'])
    else:
        command.extend(['--offset', '1760'])
        command.extend(['--length', '288'])
    command.extend(['--file', filename])
    run_command(command)

    signed_file = os.path.splitext(filename)[0] + '.sig'
    sig_type = "nvidia-rsa"
    command = exec_file('tegrahost')
    if int(values['--chip'], 0) in [0x19, 0x23]:
        command.extend(['--chip', values['--chip'], values['--chip_major']])
    command.extend(['--updatesigheader', filename, signed_file, sig_type])
    run_command(command)

    shutil.copyfile(filename, out_file)
    return out_file

def tegraflash_oem_encrypt_and_sign_file(in_file, header , magic_id):
    filename = os.path.basename(in_file)
    mode = tegrasign_values['--mode']
    command = exec_file('tegrahost')
    command.extend(['--chip', values['--chip']])
    command.extend(['--align', in_file])
    run_command(command)

    if not os.path.exists(filename):
        tegraflash_symlink(in_file, filename)

    mode = 'oem-rsa-sbk'
    if bool(header) ==True:
        if int(values['--chip'], 0) == 0x18:
            command = exec_file('tegrahost')
            command.extend(['--appendsigheader', filename, mode])
            run_command(command)
            filename = os.path.splitext(filename)[0] + '_sigheader' + os.path.splitext(filename)[1]
    else:
        if int(values['--chip'], 0) == 0x19:
                    command = exec_file('tegrahost')
                    command.extend(['--appendsigheader', filename, mode])
                    command.extend(['--chip', values['--chip'], values['--chip_major']])
                    command.extend(['--magicid', magic_id])
                    run_command(command)
                    if not _is_header_present(filename):
                        filename = os.path.splitext(filename)[0] + '_sigheader' + os.path.splitext(filename)[1]

    root = ElementTree.Element('file_list')
    comment = ElementTree.Comment('Auto generated by tegraflash.py')
    root.append(comment)
    child = ElementTree.SubElement(root, 'file')
    child.set('name', filename)
    if bool(header) == True:
        if int(values['--chip'], 0) == 0x19:
           if not _is_header_present(filename):
              child.set('offset', '0')
           else:
              child.set('offset', '4096')

        else :
            child.set('offset', '400')
    else:
        if int(values['--chip'], 0) == 0x19:
           child.set('offset', '2960')
           child.set('length', '1136')
        else :
           child.set('offset', '384')
    sbk = ElementTree.SubElement(child, 'sbk')
    sbk.set('encrypt', '1')
    sbk.set('sign', '1')
    sbk.set('encrypt_file', filename + '.encrypt')
    sbk.set('hash', filename + '.hash')
    pkc = ElementTree.SubElement(child, 'pkc')
    pkc.set('signature', filename + '.sig')
    pkc.set('signed_file', filename + '.signed')
    ec = ElementTree.SubElement(child, 'ec')
    ec.set('signature', filename + '.sig')
    ec.set('signed_file', filename + '.signed')
    eddsa = ElementTree.SubElement(child, 'eddsa')
    eddsa.set('signature', filename + '.sig')
    eddsa.set('signed_file', filename + '.signed')
    sign_tree = ElementTree.ElementTree(root);
    sign_tree.write(filename + '_list.xml')

    command = exec_file('tegrasign')
    if bool(header) == True:
        command.extend(['--key'] + [values['--encrypt_key'][0]])
    else:
        command.extend(['--key'] + values['--key'])
        command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])
    command.extend(['--list', filename + '_list.xml'])
    if int(values['--chip'], 0) == 0x19:
        if mode == 'oem-rsa':
            if os.path.isfile(tegrasign_values['--getmontgomeryvalues']):
                command.extend(['--getmontgomeryvalues', tegrasign_values['--getmontgomeryvalues']])
    run_command(command)

    sign_xml_file = filename + '_list_signed.xml'

    with open(sign_xml_file, 'rt') as file:
        xml_tree = ElementTree.parse(file)

    mode = xml_tree.getroot().get('mode')
    if mode == "pkc" or mode == "ec" or mode == "eddsa":
        list_text = "signed_file"
        sig_file = "signature"
        if mode == "pkc":
           sig_type = "oem-rsa"
        if mode == "ec":
           sig_type = "oem-ecc"
        if mode == "eddsa":
           sig_type = "oem-eddsa"
    else:
        list_text = "encrypt_file"
        sig_type = "zerosbk"
        sig_file = "hash"

    signed_file = filename
    for file_nodes in xml_tree.iter('file'):
        signed_file = file_nodes.find(mode).get(list_text)
        sig_file = file_nodes.find(mode).get(sig_file)

    command = exec_file('tegrahost')
    if int(values['--chip'], 0) == 0x19:
        command.extend(['--chip', values['--chip'], values['--chip_major']])

    command.extend(['--updatesigheader', signed_file, sig_file, sig_type])
    if sig_type is not "zerosbk":
        if os.path.isfile(tegrasign_values['--pubkeyhash']):
           command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])
    if sig_type is "oem-rsa":
        if os.path.isfile(tegrasign_values['--getmontgomeryvalues']):
            command.extend(['--setmontgomeryvalues', tegrasign_values['--getmontgomeryvalues']])

    run_command(command)

    signed_file = os.path.splitext(signed_file)[0] + os.path.splitext(signed_file)[1]
    return signed_file

def tegraflash_t21x_sign_file(magicid, in_file):
    filename = os.path.basename(in_file)
    mode = tegrasign_values['--mode']
    command = exec_file('tegrahost')
    command.extend(['--chip', values['--chip']])
    command.extend(['--align', in_file])
    run_command(command)
    if not os.path.exists(filename):
        tegraflash_symlink(in_file, filename)

    if mode == 'pkc':
        mode = 'oem-rsa'
    out_file = filename + "_blheader"

    command = exec_file('tegrahost')
    command.extend(['--magicid', magicid])
    command.extend(['--appendsigheader', filename, out_file])
    run_command(command)

    root = ElementTree.Element('file_list')
    comment = ElementTree.Comment('Auto generated by tegraflash.py')
    root.append(comment)
    child = ElementTree.SubElement(root, 'file')
    child.set('name', out_file)
    child.set('offset', '560')
    sbk = ElementTree.SubElement(child, 'sbk')
    sbk.set('encrypt', '1')
    sbk.set('sign', '1')
    sbk.set('encrypt_file', out_file + '.encrypt')
    sbk.set('hash', out_file + '.hash')
    pkc = ElementTree.SubElement(child, 'pkc')
    pkc.set('signature', out_file + '.sig')
    pkc.set('signed_file',out_file)

    sign_tree = ElementTree.ElementTree(root);
    sign_tree.write(filename + '_list.xml')

    command = exec_file('tegrasign')
    command.extend(['--key'] + values['--key'])
    command.extend(['--list', filename + '_list.xml'])
    if os.path.isfile(tegrasign_values['--pubkeyhash']):
        command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])
    run_command(command)

    sign_xml_file = filename + '_list_signed.xml'

    with open(sign_xml_file, 'rt') as file:
        xml_tree = ElementTree.parse(file)
    mode = xml_tree.getroot().get('mode')
    if mode == "pkc":
        sig_type = "oem-rsa"
        list_text = "signed_file"
        sig_file = "signature"
    else:
        list_text = "encrypt_file"
        sig_type = "zerosbk"
        sig_file = "hash"

    #signed_file = filename

   # signed_file = filename
    for file_nodes in xml_tree.iter('file'):
        signed_file = file_nodes.find(mode).get(list_text)
        sig_file = file_nodes.find(mode).get(sig_file)
    if mode == "pkc":
        pkc_file = filename + '.signed'
    else:
        pkc_file = filename + '.encrypt'
    #    signed_file = filename
    command = exec_file('tegrahost')
    command.extend(['--updatesigheader', signed_file, sig_file, sig_type])
    if os.path.isfile(tegrasign_values['--pubkeyhash']):
        command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])
    run_command(command)

    #if mode == "pkc":
    shutil.copyfile(signed_file, pkc_file)
    return pkc_file

def tegraflas_oem_sign_file(in_file, magic_id):
    filename = os.path.basename(in_file)
    mode = tegrasign_values['--mode']
    command = exec_file('tegrahost')
    command.extend(['--chip', values['--chip']])
    command.extend(['--align', in_file])
    run_command(command)

    if not os.path.exists(filename):
        tegraflash_symlink(in_file, filename)

    if mode == 'pkc':
        mode = 'oem-rsa'
    else :
        if mode == 'ec':
            mode = 'oem-ecc'
        else :
           if mode == 'eddsa':
              mode = 'oem-eddsa'

    command = exec_file('tegrahost')

    if int(values['--chip'], 0) in [0x19, 0x23]:
       command.extend(['--chip', values['--chip'], values['--chip_major']])
       #fixme : right magicid needs to be passed in recovery path
       command.extend(['--magicid', magic_id])

    if values['--minratchet_config'] is not None:
       command.extend(['--ratchet_blob', tegrahost_values['--ratchet_blob']])

    command.extend(['--appendsigheader', filename, mode])
    run_command(command)
    filename = os.path.splitext(filename)[0] + '_sigheader' + os.path.splitext(filename)[1]

    root = ElementTree.Element('file_list')
    comment = ElementTree.Comment('Auto generated by tegraflash.py')
    root.append(comment)
    child = ElementTree.SubElement(root, 'file')
    child.set('name', filename)
    # fixed offsets for BCH
    if int(values['--chip'], 0) in [0x19, 0x23]:
        child.set('offset', '2960')
        child.set('length', '1136')
    else :
        child.set('offset', '384')
    sbk = ElementTree.SubElement(child, 'sbk')
    sbk.set('encrypt', '1')
    sbk.set('sign', '1')
    sbk.set('encrypt_file', filename + '.encrypt')
    sbk.set('hash', filename + '.hash')
    pkc = ElementTree.SubElement(child, 'pkc')
    pkc.set('signature', filename + '.sig')
    pkc.set('signed_file', filename + '.signed')
    ecc = ElementTree.SubElement(child, 'ec')
    ecc.set('signature', filename + '.sig')
    ecc.set('signed_file', filename + '.signed')
    eddsa = ElementTree.SubElement(child, 'eddsa')
    eddsa.set('signature', filename + '.sig')
    eddsa.set('signed_file', filename + '.signed')

    sign_tree = ElementTree.ElementTree(root);
    sign_tree.write(filename + '_list.xml')

    command = exec_file('tegrasign')
    command.extend(['--key'] + values['--key'])
    command.extend(['--list', filename + '_list.xml'])
    command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])
    if int(values['--chip'], 0) in [0x19, 0x23] :
        if mode == 'oem-rsa':
           command.extend(['--getmontgomeryvalues', tegrasign_values['--getmontgomeryvalues']])
    run_command(command)

    sign_xml_file = filename + '_list_signed.xml'

    with open(sign_xml_file, 'rt') as file:
        xml_tree = ElementTree.parse(file)

    mode = xml_tree.getroot().get('mode')
    if mode == "pkc":
        sig_type = "oem-rsa"
        list_text = "signed_file"
        sig_file = "signature"
    else:
        if mode == "ec":
            sig_type = "oem-ecc"
            list_text = "signed_file"
            sig_file = "signature"
        else:
            if mode == "eddsa":
                sig_type = "oem-eddsa"
                list_text = "signed_file"
                sig_file = "signature"
            else :
                list_text = "encrypt_file"
                sig_type = "zerosbk"
                sig_file = "hash"

    signed_file = filename
    for file_nodes in xml_tree.iter('file'):
        signed_file = file_nodes.find(mode).get(list_text)
        sig_file = file_nodes.find(mode).get(sig_file)

    command = exec_file('tegrahost')

    if int(values['--chip'], 0) in [0x19, 0x23] :
        command.extend(['--chip', values['--chip'], values['--chip_major']])
        if os.path.isfile(tegrasign_values['--pubkeyhash']):
            command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])
        if os.path.exists(tegrasign_values['--getmontgomeryvalues']):
            command.extend(['--setmontgomeryvalues', tegrasign_values['--getmontgomeryvalues']])

    command.extend(['--updatesigheader', signed_file, sig_file, sig_type])

    run_command(command)

    signed_file = os.path.splitext(signed_file)[0] + os.path.splitext(signed_file)[1]

    return signed_file

def tegraflash_verify_emmc(test_args):
    info_print('Verifying EMMC')
    command = exec_file('tegrarcm')
    command.extend(['--oem', 'verifyemmc'])
    command.extend(test_args)
    run_command(command)

def tegraflash_verify_eeprom(test_args):
    info_print('Verifying EEPROM')
    command = exec_file('tegrarcm')
    command.extend(['--oem', 'verifyeeprom'])
    command.extend(test_args)
    run_command(command)

def tegraflash_readmrr(args, test_args):
    info_print('Reading MRR')

    values.update(args)

    if values['--securedev']:
        tegraflash_send_tboot(args['--applet'])
    else:
        tegraflash_generate_rcm_message()
        tegraflash_send_tboot(tegrarcm_values['--signed_list'])

    args['--skipuid'] = False

    if values['--bct'] is not None:
        tegraflash_generate_bct()
        tegraflash_send_bct()

    command = exec_file('tegrarcm')
    command.extend(['--oem', 'readmrr'])
    run_command(command)

def tegraflash_write_partition(executable, partition_name, filename):
    info_print('Writing partition')
    command = exec_file(executable)
    command.extend(['--write', partition_name, filename])
    run_command(command)

def tegraflash_ccg_update_fw(filename1, filename2):
    info_print('Package CCG firmware')
    command = exec_file('tegrahost')
    command.extend(['--packageccg', filename1, filename2, 'ccg-fw.bin'])
    run_command(command)

    info_print('Update CCG firmware')
    command = exec_file('tegradevflash')
    command.extend(['--ccgupdate', 'ccg-fw.bin'])
    run_command(command)

def tegraflash_packageccg(exports, args):
    values.update(exports)
    info_print('Package CCG firmware')
    if len(args) >= 2:
        filename1 = tegraflash_abs_path(args[0])
        filename2 = tegraflash_abs_path(args[1])
        outfile = 'ccg-fw.bin'
        if len(args) == 3:
            outfile = args[2]
        outfile = tegraflash_abs_path(outfile)
    command = exec_file('tegrahost')
    command.extend(['--packageccg', filename1, filename2, outfile])
    run_command(command)

def tegraflash_erase_partition(partition_name):
    info_print('Writing partition')
    command = exec_file('tegradevflash')
    command.extend(['--erase', partition_name])
    run_command(command)

def tegraflash_verify(args):
    info_print("Verifying Partitions")
    command = exec_file('tegradevflash')
    command.extend(['--verify'])
    run_command(command)

def tegraflash_setverify_partition(partition_name):
    info_print('Setting Partition Verification')
    command = exec_file('tegradevflash')
    command.extend(['--setverify', partition_name])
    run_command(command)

def tegraflash_read_partition(executable, partition_name, filename):
    info_print('Reading partition')
    command = exec_file(executable)
    command.extend(['--read', partition_name, filename])
    run_command(command)

def exec_file(name):
    bin_name = tegraflash_binaries[name]

    if sys.platform == 'win32' or sys.platform == 'cygwin':
        bin_name = bin_name + '.exe'

    use_shell = False
    if sys.platform == 'win32':
        use_shell = True

    cmd_environ["PATH"] = '/home/lena/Desktop/docker-builder/NVIDIA'

    try:
        subprocess.Popen([bin_name ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=use_shell, env=cmd_environ)
    except OSError as e:
        raise tegraflash_exception('Could not find ' + bin_name)

    supports_instance = ['tegrarcm', 'tegradevflash']
    if values['--instance'] is not None and name in supports_instance:
        bin_name = [bin_name, '--instance', values['--instance']]
    else:
        bin_name = [bin_name]

    return bin_name

def tegraflash_send_tboot(file_name):
    global uidlog
    info_print('Boot Rom communication')
    command = exec_file('tegrarcm')
    command.extend(['--chip', values['--chip'], values['--chip_major']])
    if values['--applet_softfuse']:
        soft_fuse = values['--applet_softfuse']
        command.extend(['--rcm', soft_fuse])
    command.extend(['--rcm', file_name])

    if values['--skipuid']:
        command.extend(['--skipuid'])
        values['--skipuid'] = False

    uidlog = run_command(command, True)
    tegraflash_poll_applet_bl()

def tegraflash_send_bct():
    # non-secure case generate bct at run time
    if values['--securedev'] and not tegrabct_values['--updated']:
        tegraflash_update_boardinfo(tegrabct_values['--bct'])
        tegraflash_update_odmdata(tegrabct_values['--bct'])
        if int(values['--chip'], 0) == 0x21 and int(values['--chip_major'], 0) > 1:
            tegraflash_update_boardinfo(tegrabct_values['--rcm_bct'])
            tegraflash_update_odmdata(tegrabct_values['--rcm_bct'])

    info_print('Sending BCTs')

    if int(values['--chip'], 0) == 0x21 and int(values['--chip_major'], 0) > 1:
        tegraflash_update_bfs_images()
    command = exec_file('tegrarcm')
    if values['--tegraflash_v2']:
        command.extend(['--download', 'bct_bootrom', tegrabct_values['--bct']])
        command.extend(['--download', 'bct_mb1', tegrabct_values['--mb1_bct']])
        if int(values['--chip'], 0) == 0x19:
            command.extend(['--download', 'bct_mem', tegrabct_values['--membct_rcm']])
    elif int(values['--chip'], 0) == 0x21 and int(values['--chip_major'], 0) > 1:
        command.extend(['--download', 'bct', tegrabct_values['--rcm_bct']])
    else:
        command.extend(['--download', 'bct', tegrabct_values['--bct']])

    run_command(command)

def tegraflash_get_storage_info():
    info_print('Retrieving storage infomation')
    try:
        command = exec_file('tegrarcm')
        command.extend(['--oem', 'platformdetails', 'storage', tegrarcm_values['--storage_info']])
        run_command(command)
    except tegraflash_exception as e:
        command = exec_file('tegradevflash')
        command.extend(['--oem', 'platformdetails', 'storage', tegrarcm_values['--storage_info']])
        run_command(command)

def check_ismb1():
    try:
        command = exec_file('tegrarcm')
        command.extend(['--isapplet'])
        run_command(command)
        return True
    except tegraflash_exception as e:
        return False

def check_ismb2():
    if int(values['--chip'], 0) != 0x19 :
        return False

    try:
        command = exec_file('tegrarcm')
        command.extend(['--ismb2'])
        run_command(command)
        return True
    except tegraflash_exception as e:
        return False

def check_iscpubl():
    try:
        command = exec_file('tegradevflash')
        command.extend(['--iscpubl'])
        run_command(command)
        return True
    except tegraflash_exception as e:
        return False

def tegraflash_send_mb2_applet():
    filename = None
    bins = values['--bins'].split(';')
    for binary in bins:
        binary = binary.strip(' ')
        binary = binary.replace('  ', ' ')
        tags = binary.split(' ')
        if tags[0] == 'mb2_applet':
            filename = tags[1]
            break
    if filename is None:
        raise tegraflash_exception('mb2 applet not found in --bins')

    if values['--encrypt_key'] is not None:
        filename = tegraflash_oem_encrypt_and_sign_file(filename, True, 'PLDT')
        filename = tegraflash_oem_encrypt_and_sign_file(filename, False, 'PLDT')
    else:
        filename = tegraflas_oem_sign_file(filename, 'PLDT')
    command = exec_file('tegrarcm')
    command.extend(['--download', 'mb2', filename])
    run_command(command)

def tegraflash_boot_mb2_applet():
    filename = tegraflash_send_mb2_applet()
    tegraflash_boot('recovery')

    count = 30
    while count is not 0 and not check_ismb2():
        time.sleep(1)
        count = count - 1

def tegraflash_poll_applet_bl():
    if not values['--tegraflash_v2']:
        return
    count = 30
    enable_print = True
    while count is not 0:
        time.sleep(1)
        count = count - 1
        if check_ismb1() or check_ismb2() or check_iscpubl():
            return

    if count == 0:
        raise tegraflash_exception('None of the bootloaders are running on device. Check the UART log.')

def tegraflash_send_bootimages():
    info_print('Sending boot.img and required binaries')
    command = exec_file('tegrarcm')

    if values['--fb'] is not None:
        command.extend(['--download', 'fb', values['--fb'], '0', '0'])

    if values['--lnx'] is not None:
        command.extend(['--download', 'lnx', values['--lnx'], '0', '0'])

    if not (values['--tos'] is None):
        command.extend(['--download', 'tos', values['--tos'], '0', '0'])
        if  not (values['--eks'] is None):
            command.extend(['--download', 'eks', values['--eks'], '0', '0'])

    if values['--wb'] is not None:
        command.extend(['--download', 'wb0', values['--wb'], '0', '0'])

    if values['--kerneldtb'] is not None:
        command.extend(['--download', 'dtb', values['--kerneldtb'], '0'])

    if values['--bpfdtb'] is not None:
        command.extend(['--download', 'bpd', values['--bpfdtb'], '0'])

    if values['--bpf'] is not None:
        command.extend(['--download', 'bpf', values['--bpf'], '0'])

    run_command(command)

def tegraflash_generate_recovery_blob(exports, recovery_args):
    values.update(exports)
    output_dir = tegraflash_abs_path('dev_images')

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    tegraflash_get_key_mode()
    if not recovery_args[0]:
        blob_filename =  'blob.bin'
    else:
        blob_filename = recovery_args[0]

    tegraflash_generate_blob(True, tegraflash_os_path(output_dir + "/" + blob_filename))
    info_print(blob_filename + ' saved in ' + output_dir)

def tegraflash_generate_blob(sign_images, blob_filename):
    bins=''
    info_print('Generating blob')
    root = ElementTree.Element('file_list')
    root.set('mode', 'blob')
    comment = ElementTree.Comment('Auto generated by tegraflash.py')
    root.append(comment)
    child = ElementTree.SubElement(root, 'file')
    filename = os.path.basename(values['--bl'])

    if not os.path.exists(filename):
        tegraflash_symlink(tegraflash_abs_path(values['--bl']), filename)

    if not os.path.exists('blob_' + filename):
        tegraflash_symlink(filename, 'blob_' + filename)

    filename = 'blob_' + filename;

    if sign_images:
        filename = tegraflas_oem_sign_file(filename, 'CPBL')

    child.set('name', filename)
    child.set('type', 'bootloader')

    if int(values['--chip'], 0) == 0x18:
        images_to_sign = ['mts_preboot', 'mts_bootpack', 'mts_mce', 'mts_proper', 'mb2_bootloader', 'fusebypass', 'bootloader_dtb', 'spe_fw', 'bpmp_fw', 'bpmp_fw_dtb', 'tlk', 'eks', 'sce_fw', 'adsp_fw', 'kernel', 'kernel_dtb']
    else:
        images_to_sign = ['mts_preboot', 'mts_bootpack', 'mts_mce', 'mts_proper', 'mb2_bootloader', 'fusebypass', 'bootloader_dtb', 'spe_fw', 'bpmp_fw', 'bpmp_fw_dtb', 'tlk', 'eks', 'sce_fw', 'adsp_fw']

    if values['--bins']:
        bins = values['--bins'].split(';')

    for binary in bins:
        binary = binary.strip(' ')
        binary = binary.replace('  ', ' ')
        tags = binary.split(' ')
        child = ElementTree.SubElement(root, 'file')
        if (len(tags) < 2):
            raise tegraflash_exception('invalid format ' + binary)

        child.set('type', tags[0])

        filename = os.path.basename(tags[1])
        if not os.path.exists(filename):
            tegraflash_symlink(tegraflash_abs_path(tags[1]), filename)

        if not os.path.exists('blob_' + filename):
            tegraflash_symlink(filename, 'blob_' + filename)

        filename = 'blob_' + filename;

        if sign_images and tags[0] in images_to_sign:
            magic_id = tegraflash_get_magicid(tags[0])
            filename = tegraflas_oem_sign_file(filename, magic_id)

        child.set('name', filename)

        if (len(tags) > 2):
            child.set('load_address', tags[2])

    blobtree = ElementTree.ElementTree(root);
    blobtree.write('blob.xml')

    command = exec_file('tegrahost')
    command.extend(['--chip', values['--chip']])
    command.extend(['--generateblob', 'blob.xml', blob_filename])

    run_command(command)

def tegraflash_t210_sign_bootloader_binaries(signed_images = True):
    binaries={}
    binaries['bl'] = values['--bl']
    binaries['bldtb'] = values['--bldtb']
    if not signed_images:
        return binaries

    images_to_sign = {"DTB": "bldtb", "EBT": "bl"}

    if values['--bins'] is not None:
        bins = values['--bins'].split(';')
        for binary in bins:
            binary = binary.strip(' ')
            binary = binary.replace('  ', ' ')
            tags = binary.split(' ')
            if (len(tags) < 2):
                raise tegraflash_exception('invalid format ' + binary)

            if tags[0] in images_to_sign:
                tags[1] = tegraflash_t21x_sign_file(tags[0], tags[1])
                binaries[images_to_sign[tags[0]]] = tags[1]

    return binaries

def tegraflash_send_bootloader(sign_images = True):
    bl = values['--bl']
    bldtb = values['--bldtb']
    if values['--tegraflash_v2']:
        tegraflash_generate_blob(sign_images, 'blob.bin')
    elif int(values['--chip'], 0) == 0x21 and int(values['--chip_major'], 0) == 0 and sign_images:
        binaries = tegraflash_t210_sign_bootloader_binaries()
        bl = binaries['bl']
        bldtb = binaries['bldtb']

    info_print('Sending bootloader and pre-requisite binaries')
    command = exec_file('tegrarcm')

    if values['--tegraflash_v2']:
        command.extend(['--download', 'blob', 'blob.bin'])
    else:
        command.extend(['--download', 'ebt', bl])
        if values['--bl-load'] is not None:
            bl_load = values['--bl-load']
        else:
            bl_load = '0'
        command.extend([bl_load, bl_load])

    if values['--applet-cpu'] is not None:
        command.extend(['--download', 'tbc', values['--applet-cpu'], '0', '0'])

    if values['--bldtb'] is not None:
        command.extend(['--download', 'rp1', bldtb, '0'])

    if values['--dtb'] is not None:
        command.extend(['--download', 'dtb', values['--dtb'], '0'])

    run_command(command)

def tegraflash_generate_devimages(cmd_args):
    info_print('Creating storage-device images')

    output_dir = tegraflash_abs_path(paths['OUT'] + '/dev_images')

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    dirsep = '/'
    if sys.platform == 'win32' or sys.platform == 'cygwin':
        dirsep = '\\'

    if values['--tegraflash_v2']:
        command = exec_file('tegraparser')
        command.extend(['--generategpt', '--pt', tegraparser_values['--pt']])
        run_command(command)

    command = exec_file('tegradevflash')
    command.extend(['--pt', tegraparser_values['--pt']])

    if not values['--tegraflash_v2']:
        command.extend(['--storageinfo', tegrarcm_values['--storage_info']])

    command.extend(['--mkdevimages', output_dir + dirsep])
    command.extend(cmd_args)

    run_command(command)

def tegraflash_flash_partitions(skipsanitize):
    info_print('Flashing the device')

    if values['--tegraflash_v2']:
        command = exec_file('tegraparser')
        command.extend(['--storageinfo', tegrarcm_values['--storage_info']])
        command.extend(['--generategpt', '--pt', tegraparser_values['--pt']])
        run_command(command)

    command = exec_file('tegradevflash')
    command.extend(['--pt', tegraparser_values['--pt']])

    if not values['--tegraflash_v2']:
        command.extend(['--storageinfo', tegrarcm_values['--storage_info']])

    if skipsanitize:
        command.extend(['--skipsanitize'])

    command.extend(['--create']);
    run_command(command)

def tegraflash_reboot(args):
    if args[0] == 'coldboot':
        info_print('Coldbooting the device')
    elif args[0] == 'recovery':
        info_print('Rebooting to recovery mode')
    else:
        raise tegraflash_exception(args[0] + " is not supported")

    if check_ismb2():
        tegraflash_tboot_reset(args)
    else:
        command = exec_file('tegradevflash')
        command.extend(['--reboot', args[0]])
        run_command(command)
        time.sleep(2)

def tegraflash_flush_sata(args):
    info_print("Start cleaning up SATA HDD internal cache (up to 10min)...")
    command = exec_file('tegradevflash')
    command.extend(['--flush_sata'])
    run_command(command)

def tegraflash_sata_fwdownload(filename):
    command = exec_file('tegradevflash')
    if filename is None:
        command.extend(['--sata_fwdownload'])
    else:
        command.extend(['--sata_fwdownload', filename])
    run_command(command)

def tegraflash_update_rpmb(args):
    values.update(args)
    if not int(values['--chip'], 0) == 0x21:
        info_print("command is not supported")
        return

    if values['--securedev']:
        tegrabct_values['--bct'] = values['--bct']
        tegrabct_values['--rcm_bct'] = values['--rcm_bct']
        tegraflash_send_tboot(args['--applet'])
        tegraflash_send_bct()
        args['--skipuid'] = False
    else:
        tegraflash_generate_rcm_message()
        tegraflash_send_tboot(tegrarcm_values['--signed_list'])
        args['--skipuid'] = False

        if values['--bct']:
            tegraflash_generate_bct()
            tegraflash_send_bct()

    if values['--tos'] and values['--eks']:
        command = exec_file('tegrarcm')
        command.extend(['--download', 'tos', values['--tos'], '0', '0'])
        command.extend(['--download', 'eks', values['--eks'], '0'])
        run_command(command)

    tegraflash_send_bootloader()
    tegraflash_boot('recovery')

    command = exec_file('tegradevflash')
    command.extend(['--oem', 'updaterpmb', values['--odmdata']])
    run_command(command)

def tegraflash_flash_bct():
    command = exec_file('tegradevflash')
    if tegrabct_values['--bct_cold_boot'] is not None:
        command.extend(['--write', 'BCT', tegrabct_values['--bct_cold_boot']]);
    else:
        command.extend(['--write', 'BCT', tegrabct_values['--bct']]);
    run_command(command)

    if values['--tegraflash_v2']:
        if tegrabct_values['--mb1_cold_boot_bct'] is not None:
            mb1_bct_parts = getPart_name_by_type(values['--cfg'], 'mb1_boot_config_table')
            for name in mb1_bct_parts:
                command = exec_file('tegradevflash')
                command.extend(['--write', name, tegrabct_values['--mb1_cold_boot_bct']]);
                run_command(command)
        else:
            command = exec_file('tegradevflash')
            command.extend(['--write', 'MB1_BCT', tegrabct_values['--mb1_bct']]);
            run_command(command)
        if tegrabct_values['--membct_cold_boot'] is not None:
            mb1_bct_parts = getPart_name_by_type(values['--cfg'], 'mem_boot_config_table')
            for name in mb1_bct_parts:
                command = exec_file('tegradevflash')
                command.extend(['--write', name, tegrabct_values['--membct_cold_boot']]);
                run_command(command)

def get_part_by_partname(cfg_file, part_name):
    file_names = []
    with open(cfg_file, 'r') as file:
        xml_tree = ElementTree.parse(file)

    root = xml_tree.getroot()

    for node in root.findall('.//partition'):
        if part_name in node.get('name'):
            if node.find('filename') is not None:
                file_names.extend([node])

    return [file_names, xml_tree]

def tegraflash_encrypt_images(skip_header):
    if values['--fb'] is not None and not values['--tegraflash_v2']:
        info_print('Updating warmboot with fusebypass information')
        command = exec_file('tegrahost')
        command.extend(['--chip', values['--chip']])
        command.extend(['--partitionlayout', tegraparser_values['--pt']])
        command.extend(['--updatewbfuseinfo', values['--fb']])
        run_command(command)

    info_print('Creating list of images to be signed')
    command = exec_file('tegrahost')
    command.extend(['--chip', values['--chip']])
    command.extend(['--partitionlayout', tegraparser_values['--pt']])
    command.extend(['--list', tegrahost_values['--list']])
    print(command)
    run_command(command)

    info_print('Generating signatures')
    command = exec_file('tegrasign')
    if bool(skip_header) == True:
       command.extend(['--key'] + values['--key'])
    else:
       command.extend(['--key', values['--encrypt_key'][0]])
    command.extend(['--list', tegrahost_values['--list']])
    command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])
    run_command(command)

def tegraflash_sign_images(ovewrite_xml = True):
    
    info_print('Creating list of images to be signed')
    command = exec_file('tegrahost')
    command.extend(['--chip', values['--chip'], values['--chip_major']])
    command.extend(['--partitionlayout', tegraparser_values['--pt']])
    command.extend(['--list', tegrahost_values['--list']])
    
    if len(values['--key']) == 3:
        command.extend(['--nkeys', '3'])

    run_command(command) # here 

    if int(values['--chip'], 0) in [0x19, 0x23]:
       info_print('Filling MB1 storage info')
       tegraflash_fill_mb1_storage_info()

    info_print('Generating signatures')
    command = exec_file('tegrasign')
    command.extend(['--key'] + values['--key'])
    command.extend(['--list', tegrahost_values['--list']])
    command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])
    if int(values['--chip'], 0) in [0x19, 0x23]:
        if  mode == 'oem-rsa':
            command.extend(['--getmontgomeryvalues', tegrasign_values['--getmontgomeryvalues']])
    run_command(command)

def tegraflash_update_images():
    info_print('Copying signatures')
    command = exec_file('tegrahost')
    command.extend(['--chip', values['--chip'], values['--chip_major']])
    command.extend(['--partitionlayout', tegraparser_values['--pt']])
    command.extend(['--updatesig', tegrahost_values['--signed_list']])

    if os.path.isfile(tegrasign_values['--pubkeyhash']):
        command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])

    if os.path.exists(tegrasign_values['--getmontgomeryvalues']):
        command.extend(['--setmontgomeryvalues', tegrasign_values['--getmontgomeryvalues']])

    if len(values['--key']) == 3:
        command.extend(['--nkeys', '3'])

    run_command(command)

def tegraflash_ignore_bfs():
    if not values['--cfg']:
        return

    if not values['--tegraflash_v2']:
        info_print('Ignore BFS information in BCT')
        command = exec_file('tegrabct')
        command.extend(['--bct', tegrabct_values['--bct']])
        command.extend(['--chip', values['--chip'], values['--chip_major']])
        command.extend(['--ignorebfs', tegraparser_values['--pt']])
        run_command(command)

def tegraflash_update_bfs_images():
    if not values['--cfg']:
        return

    if not values['--tegraflash_v2']:
        if tegrabct_values['--rcm_bct']:
            info_print('Updating BFS information on RCM BCT')
            command = exec_file('tegrabct')
            command.extend(['--bct', tegrabct_values['--rcm_bct']])
            command.extend(['--chip', values['--chip'], values['--chip_major']])
            command.extend(['--updatebfsinfo', tegraparser_values['--pt']])
            if os.path.isfile(tegrasign_values['--pubkeyhash']):
                command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])
            run_command(command)

        info_print('Updating BFS information on BCT')
        command = exec_file('tegrabct')
        command.extend(['--bct', tegrabct_values['--bct']])
        command.extend(['--chip', values['--chip'], values['--chip_major']])
        command.extend(['--updatebfsinfo', tegraparser_values['--pt']])
        if values['--ignorebfs']:
            command.extend(['--ignorebfs', tegraparser_values['--pt']])
        if os.path.isfile(tegrasign_values['--pubkeyhash']):
            command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])
        run_command(command)    # ERROR

def tegraflash_update_boardinfo(bct_file):
    if values['--nct'] is not None:
        info_print('Updating board information into bct')
        command = exec_file('tegraparser')
        command.extend(['--nct', values['--nct']])
        command.extend(['--chip', values['--chip'], values['--chip_major']])
        command.extend(['--updatecustinfo', bct_file])
        if values['--securedev']:
            command.extend(['--secure'])
        run_command(command)
        tegrabct_values['--updated'] = True
    elif values['--boardconfig'] is not None:
        info_print('Updating board information from board config into bct')
        command = exec_file('tegraparser')
        command.extend(['--boardconfig', values['--boardconfig']])
        command.extend(['--chip', values['--chip'], values['--chip_major']])
        command.extend(['--updatecustinfo', bct_file])
        run_command(command)
        tegrabct_values['--updated'] = True

def tegraflash_update_odmdata(bct_file):
    if  values['--odmdata'] is not None:
        info_print('Updating Odmdata')
        command = exec_file('tegrabct')

        if values['--tegraflash_v2']:
            command.extend(['--brbct', bct_file])
        else:
            command.extend(['--bct', bct_file])

        command.extend(['--chip', values['--chip'], values['--chip_major']])
        command.extend(['--updatefields', 'Odmdata =' + values['--odmdata']])
        run_command(command)

def _overlay_cfg(mem_cfg, overlay_cfg, out_cfg):
    command = list()
    command.extend(['sw_memcfg_overlay.pl'])
    command.extend(['-c', mem_cfg])
    command.extend(['-s', overlay_cfg])
    command.extend(['-o', out_cfg])

    run_command(command)

def apply_overlay_cfg(filename):
    cfgs = filename
    sdram_cfgs = cfgs.split(',')

    info_print('Performing cfg overlay')
    info_print(sdram_cfgs)

    mem_cfg = sdram_cfgs[0].strip()
    outfilename = mem_cfg

    memcfg_tmp = mem_cfg
    i = 0
    for cfgs in sdram_cfgs[1:]:
        cfgs = cfgs.strip()
        i = i + 1
        rnd_cfg = tempfile.NamedTemporaryFile(dir = paths['TMP'])
        tmp_cfg = rnd_cfg.name
        tmp_cfg += str(i)
        tmp_cfg += ".cfg"
        tmp_cfg = tegraflash_abs_path(tmp_cfg)
        _overlay_cfg(memcfg_tmp, cfgs, tmp_cfg)
        memcfg_tmp = tmp_cfg

    if i != 0:
        outfilename = tmp_cfg
    return outfilename

def concat_file(outfilename, infilename):
    with open(outfilename, 'a+') as outfile,open(infilename) as infile:
        outfile.write(infile.read())

def concatenate_misc_cfg():
    misc_cfgs = values['--misc_config']
    misc_cfgs = misc_cfgs.split(',')
    i = 0
    final_cfg = 'temp_misc.cfg'
    misc_cfg = misc_cfgs[0].strip()
    if misc_cfg != final_cfg :
        concat_file(final_cfg, misc_cfg)
    for cfgs in misc_cfgs[1:]:
        i = i + 1
        cfgs = cfgs.strip()
        info_print('concatenating misc cfg :' + cfgs)
        concat_file(final_cfg, cfgs)

    if i != 0:
        values['--misc_config'] = final_cfg

    if values['--misc_cold_boot_config'] is not None:
        misc_cold_boot_cfgs = values['--misc_cold_boot_config']
        misc_cold_boot_cfgs = misc_cold_boot_cfgs.split(',')
        i = 0
        final_cold_boot_cfg = 'temp_misc_cold_boot.cfg'
        misc_cold_boot_cfg = misc_cold_boot_cfgs[0].strip()
        if misc_cold_boot_cfg != final_cold_boot_cfg :
            concat_file(final_cold_boot_cfg, misc_cold_boot_cfg)
        for cfgs in misc_cold_boot_cfgs[1:]:
            i = i + 1
            cfgs = cfgs.strip()
            info_print('concatenating misc cold bootcfg :' + cfgs)
            concat_file(final_cold_boot_cfg, cfgs)

        if i != 0:
            values['--misc_cold_boot_config'] = final_cold_boot_cfg

def tegraflash_fill_mb1_storage_info():
    info_print('Generating br-bct')
    command = exec_file('tegrabct')

    if int(values['--chip'], 0) in [0x19, 0x23]:
        values['--sdram_config'] = apply_overlay_cfg(values['--sdram_config'])
        if values['--wb0sdram_config'] is not None:
            values['--wb0sdram_config'] = apply_overlay_cfg(values['--wb0sdram_config'])

    if values['--bct'] is None and int(values['--chip'], 0) in [0x18, 0x19, 0x23]:
        values['--bct'] = 'br_bct.cfg'

    if values['--tegraflash_v2']:
        brbct_arg = '--brbct'
        info_print('Updating dev and MSS params in BR BCT')
        command.extend(['--dev_param', values['--dev_params']])
        command.extend(['--sdram', values['--sdram_config']])
        command.extend(['--brbct', values['--bct']])
        tegrabct_values['--bct'] = os.path.splitext(values['--bct'])[0] + '_BR.bct'
        if values['--soft_fuses'] is not None:
            command.extend(['--sfuse', values['--soft_fuses']])
    else:
        brbct_arg = '--bct'
        command.extend(['--bct', values['--bct']])
        tegrabct_values['--bct'] = os.path.splitext(values['--bct'])[0] + '.bct'

    command.extend(['--chip', values['--chip'], values['--chip_major']])
    run_command(command)

    if tegraparser_values['--pt'] is not None:
        if not values['--tegraflash_v2']:
            info_print('Updating boot device parameters')
            command = exec_file('tegrabct')
            command.extend(['--bct', tegrabct_values['--bct']])
            command.extend(['--chip', values['--chip'], values['--chip_major']])
            command.extend(['--updatedevparam', tegraparser_values['--pt']])
            run_command(command)

        info_print('Updating bl info')
        command = exec_file('tegrabct')
        command.extend([brbct_arg, tegrabct_values['--bct']])
        command.extend(['--chip', values['--chip'], values['--chip_major']])
        if values['--blversion'] is not None:
            command.extend(['--blversion', values['--majorversion'], values['--minorversion']])
        command.extend(['--updateblinfo', tegraparser_values['--pt']])
        run_command(command)

def tegraflash_generate_br_bct(coldboot_bct):
    info_print('Generating br-bct')
    command = exec_file('tegrabct')
    bct_file = ""

    if int(values['--chip'], 0) in [0x19, 0x23]:
        values['--sdram_config'] = apply_overlay_cfg(values['--sdram_config'])
        if values['--wb0sdram_config'] is not None:
            values['--wb0sdram_config'] = apply_overlay_cfg(values['--wb0sdram_config'])

    if values['--bct'] is None and int(values['--chip'], 0) in [0x18, 0x19, 0x23]:
        values['--bct'] = 'br_bct.cfg'

    if values['--tegraflash_v2']:
        brbct_arg = '--brbct'
        info_print('Updating dev and MSS params in BR BCT')
        command.extend(['--dev_param', values['--dev_params']])
        command.extend(['--sdram', values['--sdram_config']])
        command.extend(['--brbct', values['--bct']])
        tegrabct_values['--bct'] = os.path.splitext(values['--bct'])[0] + '_BR.bct'
        if values['--soft_fuses'] is not None:
            command.extend(['--sfuse', values['--soft_fuses']])
        bct_file = tegrabct_values['--bct']
    else:
        bct_file = values['--bct']
        if not coldboot_bct:
            bct_file = os.path.splitext(values['--bct'])[0] + '_rcm.cfg'
            if not os.path.isfile(bct_file):
                tegraflash_symlink(values['--bct'], bct_file)

        brbct_arg = '--bct'
        command.extend(['--bct', bct_file])
        if coldboot_bct:
            tegrabct_values['--bct'] = os.path.splitext(bct_file)[0] + '.bct'
            bct_file = tegrabct_values['--bct']
        else:
            tegrabct_values['--rcm_bct'] = os.path.splitext(bct_file)[0] + '.bct'
            bct_file = tegrabct_values['--rcm_bct']

    if os.path.islink(bct_file):
        os.unlink(bct_file)

    command.extend(['--chip', values['--chip'], values['--chip_major']])
    run_command(command)

    if tegraparser_values['--pt'] is not None:
        if not values['--tegraflash_v2']:
            info_print('Updating boot device parameters')
            command = exec_file('tegrabct')
            command.extend(['--bct', bct_file])
            command.extend(['--chip', values['--chip'], values['--chip_major']])
            command.extend(['--updatedevparam', tegraparser_values['--pt']])
            run_command(command)

        info_print('Updating bl info')
        command = exec_file('tegrabct')
        command.extend([brbct_arg, bct_file])
        command.extend(['--chip', values['--chip'], values['--chip_major']])
        command.extend(['--updateblinfo', tegraparser_values['--pt']])
        if values['--blversion'] is not None:
            command.extend(['--blversion', values['--majorversion'], values['--minorversion']])
        command.extend(['--updatesig', tegrahost_values['--signed_list']])
        run_command(command)

        if not values['--tegraflash_v2']:
            info_print('Updating secondary storage information into bct')
            command = exec_file('tegraparser')
            command.extend(['--pt', tegraparser_values['--pt']])
            command.extend(['--chip', values['--chip'], values['--chip_major']])
            command.extend(['--updatecustinfo', bct_file])
            run_command(command)
        else:
            info_print('Updating smd info')
            command = exec_file('tegrabct')
            command.extend([brbct_arg, bct_file])
            command.extend(['--chip', values['--chip']])
            command.extend(['--updatesmdinfo', tegraparser_values['--pt']])
            run_command(command)

    tegraflash_update_boardinfo(bct_file)
    tegraflash_update_odmdata(bct_file)

    if not values['--tegraflash_v2'] and int(values['--chip_major'], 0) >= 2 and values['--encrypt_key'] is not None:
        info_print('Get encrypt section of bct')
        command = exec_file('tegrabct')
        command.extend([brbct_arg, bct_file])
        command.extend(['--chip', values['--chip'], values['--chip_major']])
        command.extend(['--listbct', tegrabct_values['--list'], 'encrypt'])
        run_command(command)
        info_print('Encrypting bct')

        with open(tegrabct_values['--list'], 'r+') as file:
            xml_tree = ElementTree.parse(file)
            root = xml_tree.getroot()
            for child in root:
                child.find('sbk').set('encrypt', '1')
            xml_tree.write(tegrabct_values['--list'])

        command = exec_file('tegrasign')

        keys = values['--encrypt_key']
        if len(keys) == 2 and not coldboot_bct:
            keys = keys[1]
        else:
            keys = keys[0]

        command.extend(['--key', keys])
        command.extend(['--list', tegrabct_values['--list']])
        run_command(command)

        with open(tegrabct_values['--list'], 'r+') as file:
            xml_tree = ElementTree.parse(file)
            root = xml_tree.getroot()
            for child in root:
                sbk_file = child.find('sbk').attrib.get('encrypt_file')
                shutil.copyfile(sbk_file, bct_file)

    if int(values['--chip'], 0) == 0x21:
        info_print('Get Signed section of bct')
        command = exec_file('tegrabct')
        command.extend([brbct_arg, bct_file])
        command.extend(['--chip', values['--chip'], values['--chip_major']])
        command.extend(['--listbct', tegrabct_values['--list']])
        run_command(command)

        info_print('Signing BCT')
        command = exec_file('tegrasign')
        if values['--encrypt_key'] is not None:
           info_print('Generating signatures')
           command = exec_file('tegrasign')
           command.extend(['--key', values['--encrypt_key'][0]])
           command.extend(['--list', tegrabct_values['--list']])
           command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])
           run_command(command)

           info_print('Updating BCT with signature')
           command = exec_file('tegrabct')
           command.extend([brbct_arg, bct_file])
           command.extend(['--chip', values['--chip']])
           command.extend(['--updatesig', tegrabct_values['--signed_list']])

           if os.path.isfile(tegrasign_values['--pubkeyhash']):
               command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])

           run_command(command)

        command = exec_file('tegrasign')
        command.extend(['--key'] + values['--key'])
        command.extend(['--list', tegrabct_values['--list']])
        command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])
        run_command(command)

        info_print('Updating BCT with signature')
        command = exec_file('tegrabct')
        command.extend([brbct_arg, bct_file])
        command.extend(['--chip', values['--chip'], values['--chip_major']])
        command.extend(['--updatesig', tegrabct_values['--signed_list']])

        if os.path.isfile(tegrasign_values['--pubkeyhash']):
            command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])

        if os.path.exists(tegrasign_values['--getmontgomeryvalues']):
            command.extend(['--setmontgomeryvalues', tegrasign_values['--getmontgomeryvalues']])

        run_command(command)

    if values['--encrypt_key'] is not None and int(values['--chip'], 0) != 0x21:
        info_print('Get encrypted section of bct')
        command = exec_file('tegrabct')
        command.extend([brbct_arg, tegrabct_values['--bct']])
        command.extend(['--chip', values['--chip'], values['--chip_major']])
        if int(values['--chip'], 0) == 0x19:
            command.extend(['--listencbct', tegrabct_values['--list']])
        else:
            command.extend(['--listbct', tegrabct_values['--list']])
        run_command(command)

        info_print('Signing BCT')
        command = exec_file('tegrasign')
        if values['--encrypt_key'] is not None:
           info_print('Generating signatures with encryption')
           command = exec_file('tegrasign')
           command.extend(['--key', values['--encrypt_key'][0]])
           if int(values['--chip'], 0) == 0x19:
               command.extend(['--offset', '2328'])
               command.extend(['--file', bct_file])
           else :
               command.extend(['--list', tegrabct_values['--list']])
               command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])
           run_command(command)

           info_print('Updating BCT with signature')
           if int(values['--chip'], 0) != 0x19:
               command = exec_file('tegrabct')
               command.extend([brbct_arg, bct_file])
               command.extend(['--chip', values['--chip']])
               command.extend(['--updatesig', tegrabct_values['--signed_list']])

               if os.path.isfile(tegrasign_values['--pubkeyhash']):
                   command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])

               run_command(command)
           else:
                with open(tegrabct_values['--list'], 'r+') as file:
                    xml_tree = ElementTree.parse(file)
                    root = xml_tree.getroot()
                    for child in root:
                        sbk_file = child.find('sbk').attrib.get('encrypt_file')
                        sbk_file =sbk_file.replace('br_bct_BR.bct.encrypt' ,'br_bct_BR_encrypt.bct')
                        shutil.copyfile(sbk_file, bct_file)

    if int(values['--chip'], 0) != 0x21:
        info_print('Get Signed section of bct')
        command = exec_file('tegrabct')
        command.extend([brbct_arg, tegrabct_values['--bct']])
        command.extend(['--chip', values['--chip'], values['--chip_major']])
        command.extend(['--listbct', tegrabct_values['--list']])
        run_command(command)

        command = exec_file('tegrasign')
        command.extend(['--key'] + values['--key'])
        command.extend(['--list', tegrabct_values['--list']])
        command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])
        if int(values['--chip'], 0) in [0x19, 0x23]:
            command.extend(['--getmontgomeryvalues', tegrasign_values['--getmontgomeryvalues']])
        run_command(command)

        info_print('Updating BCT with signature')
        command = exec_file('tegrabct')
        command.extend([brbct_arg, bct_file])
        command.extend(['--chip', values['--chip'], values['--chip_major']])
        command.extend(['--updatesig', tegrabct_values['--signed_list']])

        if os.path.isfile(tegrasign_values['--pubkeyhash']):
            command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])

        if os.path.exists(tegrasign_values['--getmontgomeryvalues']):
            command.extend(['--setmontgomeryvalues', tegrasign_values['--getmontgomeryvalues']])
        run_command(command)

# Convert BPMP DTSI to BPMP DTB
def tegraflash_bpmp_dtsi_to_dtb(bpmp_dtb_path, test_dts):
    bpmp_dtb_dir = os.path.dirname(bpmp_dtb_path)
    if not os.path.exists(test_dts):
        info_print("test dts not present")
        return False

    # Modify file permissions to regenerate the dtb
    os.chmod(bpmp_dtb_path, 0o755)
    try:
        command = exec_file('dtc')
        command.extend(['-qqq','-I', 'dts', '-O', 'dtb', '-f', test_dts, '-o', bpmp_dtb_path])
        run_command(command, False)
        # Set default permissions -rw-rw-r--
        os.chmod(bpmp_dtb_path, 0o664)
    except Exception as e:
        info_print("dtc failed to convert dtsi to dtb")
        return False
    return True

def tegraflash_bpmp_remove_unused_phandles(ramcode, lines, test_dts, valid_entry,
                    strap_id_line_num, strap_ids_ph_str, dtb_start_pos,
                    dtb_end_pos):
    if not os.path.exists(test_dts):
        info_print("dtsi file not present - " + test_dts)
        return False

    # Remove unused strap id phandles
    for line_num in range(0, len(lines)):
        if line_num == strap_id_line_num:
            for phandle in strap_ids_ph_str:
                if phandle != strap_ids_ph_str[ramcode]:
                    lines[line_num] = re.sub(phandle, '0x0', lines[line_num])

    invalid = False
    try:
        with open(test_dts, "w") as fp:
            for line_num in range(0, len(lines)):
                for i in range(0, len(dtb_start_pos)):
                    if ((line_num >= dtb_start_pos[i]) and
                        (line_num <= dtb_end_pos[i]) and
                            not valid_entry[i]):
                        invalid = True
                        break
                    else:
                        invalid = False

                if invalid is False:
                    fp.write(lines[line_num])
    except Exception as e:
        info_print("Could not open dts in write mode - " + test_dts)
        return False
    return lines

# Check for phandle from each of the dtb_start_pos and delete position if
# phandle is correct.
def tegraflash_bpmp_update_valid_entries(ramcode, lines, dtb_start_pos,
        dtb_end_pos, strap_ids_ph_str):
    trimmed_lines = lines
    valid_entry = []

    for i in range(0, len(dtb_start_pos)):
        for line_num in range(dtb_start_pos[i], dtb_end_pos[i]):
            if "phandle" in lines[line_num] and not "linux" in lines[line_num]:
                cur_strap_id = re.search('<(.+?)>', lines[line_num]).group(1)
                if cur_strap_id == strap_ids_ph_str[ramcode]:
                    valid_entry.append(True)
                else:
                    valid_entry.append(False)

    return valid_entry

# Saves line position for all external-memory-* entries in bpmp dts file
def tegraflash_bpmp_save_table_pos(lines):
    dtb_start_pos = []
    dtb_end_pos = []
    count = -1

    # DTB syntax uses matching brackets. Leveraging the same to bound the
    # necessary start and end positions strap entries.
    # Example -
    #   external-memory-0 {         -------> start pos for the strap id 0
    #       compatible = "nvidia,t19x-emc-table";
    #       phandle = <0xa>;
    #       ...
    #       foo1 {  ---> neglected(sub node)
    #       ...
    #       };      ---> neglected(sub node)
    #   };                          -------> end pos for the strap id 0
    for i in range(0, len(lines)):
        if "external-memory-" in lines[i]:
            dtb_start_pos.append(i)
            count = count + 1
            continue

        if "{" in lines[i]:
            count = count + 1
        if "}" in lines[i]:
            count = count - 1

        # start pos and end pos are a set of pairs. If the start pos is not
        # detected in the dts file, end pos detected should not be saved.
        if count == 0 and (len(dtb_start_pos) + len(dtb_end_pos))%2 == 1:
            dtb_end_pos.append(i + 1)

    if (len(dtb_start_pos) == 0 or
        len(dtb_end_pos) == 0 or
        (len(dtb_start_pos) != len(dtb_end_pos))):
        return -1, -1

    return dtb_start_pos, dtb_end_pos

# Get the strap phandle entries
def tegraflash_bpmp_get_strap_handles(ramcode, test_dts):
    lines = []
    strap_ids_ph_str = []
    strap_id_line_num = 0

    if os.path.exists(test_dts):
        with open(test_dts, "r") as fp:
            lines = fp.readlines()
    else:
        info_print("Test dts not present - " + test_dts)
        return -1

    for i in range(0, len(lines)):
        if "emc-strap" in lines[i]:
            line = lines[i + 1];
            strap_id_line_num = i + 1
            # Strip to get the available strap-ids
            #   emc-strap {
            #       select = <0xa 0x0 0x0 0x0>;
            #   };
            strap_ids_ph_str = re.search('<(.+?)>', line).group(1)
            strap_ids_ph_str = strap_ids_ph_str.split(' ')
            break

    if len(strap_ids_ph_str) == 0:
        info_print("No emc strap-id entries present in BPMP dtb")
        os.remove(test_dts)
        return -1

    if ramcode  > len(strap_ids_ph_str):
        info_print("BPMP FW DTB does not contain emc-strap " +
                        str(ramcode) + " data")

    return lines, strap_ids_ph_str, strap_id_line_num

# Convert the DTB to DTSI
def tegraflash_bpmp_generate_int_dtsi(bpmp_dtb_dir, bpmp_dtb_path):
    test_dts = bpmp_dtb_dir + "/test.dts"
    if os.path.exists(test_dts):
        os.remove(test_dts)
    command = exec_file('dtc')
    command.extend(['-qqq','-I', 'dtb', bpmp_dtb_path, "-o", test_dts])
    run_command(command, False)

    if not os.path.exists(test_dts):
        info_print("dtc command Failed to create dtsi file from dtb")
        return ""

    return test_dts

def tegraflash_bpmp_generate_dtb(ramcode):
    info_print("Generating BPMP dtb for ramcode - " + str(ramcode))
    bpmp_bin_key = "bpmp_fw_dtb"
    bins = values['--bins'].split(';')
    for binary in bins:
        binary = binary.strip(' ')
        binary = binary.replace('  ', ' ')
        tags = binary.split(' ')
        if tags[0] == bpmp_bin_key:
            bpmp_dtb = tags[1]
            break
    if bpmp_dtb is None:
        raise tegraflash_exception('BPMP-FW DTB not found in --bins')

    bpmp_dtb_path = tegraflash_abs_path(bpmp_dtb)
    if not os.path.exists(bpmp_dtb_path):
        info_print("Invalid BPMP DTB location - " + bpmp_dtb_path)
        info_print("")
        return

    bpmp_dtb_dir = os.path.dirname(bpmp_dtb_path)

    test_dts = tegraflash_bpmp_generate_int_dtsi(bpmp_dtb_dir, bpmp_dtb_path)
    if (test_dts == ""):
        info_print("Using existing bpmp_dtb - " + bpmp_dtb)
        info_print("")
        return

    lines = []
    strap_ids_ph_str = []
    lines, strap_ids_ph_str, strap_id_line_num = tegraflash_bpmp_get_strap_handles(ramcode, test_dts)
    if (lines == -1 or strap_ids_ph_str == -1 or strap_id_line_num == -1):
        info_print("Using existing bpmp_dtb - " + bpmp_dtb)
        info_print("")
        os.remove(test_dts)
        return

    dtb_start_pos, dtb_end_pos = tegraflash_bpmp_save_table_pos(lines) 
    if (dtb_start_pos == "-1" or dtb_end_pos == "-1"):
        info_print("Using existing bpmp_dtb " + bpmp_dtb)
        info_print("")
        os.remove(test_dts)
        return

    valid_entry = []
    valid_entry = tegraflash_bpmp_update_valid_entries(ramcode, lines,
                            dtb_start_pos, dtb_end_pos, strap_ids_ph_str)

    lines = tegraflash_bpmp_remove_unused_phandles(ramcode, lines, test_dts, valid_entry,
                        strap_id_line_num, strap_ids_ph_str,
                        dtb_start_pos, dtb_end_pos)
    if (lines == "-1"):
        os.remove(test_dts)
        info_print("Using existing bpmp_dtb " + bpmp_dtb)
        info_print("")
        return

    bpmp_dtb_size = os.stat(bpmp_dtb_path)
    ret = tegraflash_bpmp_dtsi_to_dtb(bpmp_dtb_path, test_dts)
    if not ret:
        info_print("Using existing bpmp_dtb " + bpmp_dtb)
        info_print("")
        return

    # Clean-up
    new_dtb_size = os.path.getsize(bpmp_dtb_path)
    info_print("Old BPMP dtb size - " + str(bpmp_dtb_size.st_size) + " bytes")
    info_print("New BPMP dtb size - " + str(new_dtb_size) + " bytes")
    os.remove(test_dts)
    info_print('')

def tegraflash_get_ramcode(chip_info):
    with open(chip_info, 'rb') as f:
        # RAMCODE shall be the last 4 bytes of fuses.bin
        f.seek(52, 0)
        ramcode = struct.unpack('<I',  f.read(4))[0]
        info_print('RAMCODE Read from Device: %x\n' % ramcode)
        ramcode = ramcode & 0xC
        ramcode = ramcode >> 2
    return ramcode

def tegraflash_generate_mem_bct(is_cold_boot_mb1_bct):
    if int(values['--chip'], 0) not in [0x19, 0x23]:
        return

    if bool(is_cold_boot_mb1_bct) == True:
        info_print('Generating coldboot mem-bct')
    else:
        info_print('Generating recovery mem-bct')

    command = exec_file('tegrabct')
    command.extend(['--chip', values['--chip'], values['--chip_major']])
    command.extend(['--sdram', values['--sdram_config']])
    if values['--wb0sdram_config'] is not None:
        command.extend(['--wb0sdram', values['--wb0sdram_config']])

    filename = os.path.splitext(values['--sdram_config'])[0]
    mem_bcts = [filename + "_1.bct", filename + "_2.bct", filename + "_3.bct", filename + "_4.bct",]
    command.extend(['--membct', mem_bcts[0], mem_bcts[1], mem_bcts[2], mem_bcts[3]])
    run_command(command)

    if bool(is_cold_boot_mb1_bct) == True:
        blocksize = 512
        i = 5
        if tegraparser_values['--pt'] is not None:
            info_print('Getting sector size from pt')
            command = exec_file('tegraparser')
            command.extend(['--getsectorsize', tegraparser_values['--pt'], 'sector_info.bin'])
            run_command(command)

            if os.path.isfile('sector_info.bin'):
                with open('sector_info.bin', 'rb') as f:
                    blocksize = struct.unpack('<I', f.read(4))[0]
                    info_print('BlockSize read from layout is %x\n' %blocksize)
                if blocksize not in[512, 4096]:
                    infoprint('invalid block size ')
                for i in range(1, 5):
                  if values['--encrypt_key'] is not None:
                      command = exec_file('tegrasign')
                      command.extend(['--key', values['--encrypt_key'][0]])
                      command.extend(['--file', mem_bcts[i - 1]])
                      run_command(command)
                      mem_bcts[i-1] = os.path.splitext(mem_bcts[i-1])[0] + '_encrypt'+ os.path.splitext(mem_bcts[i-1])[1]
                      i= i+1

        command = exec_file('tegrahost')
        command.extend(['--chip', values['--chip'], values['--chip_major']])
        command.extend(['--blocksize', str(blocksize)])
        command.extend(['--magicid', "MEMB"])
        command.extend(['--addsigheader_multi', mem_bcts[0], mem_bcts[1], mem_bcts[2], mem_bcts[3]])
        run_command(command)
        if values['--encrypt_key'] is not None:
            os.rename(filename + '_1_encrypt_sigheader.bct' , 'mem_coldboot.bct')
        else:
            os.rename(filename + '_1_sigheader.bct' , 'mem_coldboot.bct')

        if values['--encrypt_key'] is not None:
            tegrabct_values['--membct_cold_boot'] = tegraflash_oem_encrypt_and_sign_file('mem_coldboot.bct' ,False, 'MEMB')
        tegrabct_values['--membct_cold_boot'] = tegraflas_oem_sign_file('mem_coldboot.bct', 'MEMB')
    else:
        chip_info = tegraflash_abs_path(tegrarcm_values['--chip_info'])
        # Select 1 bct based on RAMCODE
        if os.path.isfile(chip_info):
            ramcode = tegraflash_get_ramcode(chip_info)
            os.remove(chip_info)
        else :
            chip_info_bak = tegraflash_abs_path(tegrarcm_values['--chip_info'] + '_bak')
            if os.path.exists(chip_info_bak):
                info_print("Reading ramcode from backup chip_info.bin file")
                ramcode = tegraflash_get_ramcode(chip_info_bak)
                os.remove(chip_info_bak)
            elif values['--ramcode'] is not None:
                info_print("Got ramcode " + values['--ramcode'] + " from the command line")
                ramcode = int(values['--ramcode'])
            else:
                info_print("Using default ramcode 0")
                ramcode = 0

        if bool(values['--trim_bpmp_dtb']) == False:
            info_print("Disabled BPMP dtb trim, using default dtb")
            info_print("")
        else:
            if "bpmp_fw_dtb" in values['--bins']:
                tegraflash_bpmp_generate_dtb(ramcode)

        if values['--encrypt_key'] is not None:
            shutil.copyfile(mem_bcts[ramcode], 'mem_rcm.bct')
            tegrabct_values['--membct_rcm'] = tegraflash_oem_encrypt_and_sign_file('mem_rcm.bct' ,True, 'MEMB')
            tegrabct_values['--membct_rcm'] = tegraflash_oem_encrypt_and_sign_file(tegrabct_values['--membct_rcm'] ,False, 'MEMB')
        else:
            shutil.copyfile(mem_bcts[ramcode], 'mem_rcm.bct')
            tegrabct_values['--membct_rcm'] = tegraflas_oem_sign_file('mem_rcm.bct', 'MEMB')

def tegraflash_generate_mb1_bct(is_cold_boot_mb1_bct):
    if bool(is_cold_boot_mb1_bct) == True:
        info_print('Generating coldboot mb1-bct')
    else:
        info_print('Generating recovery mb1-bct')

    command = exec_file('tegrabct')
    command.extend(['--chip', values['--chip'], values['--chip_major']])

    tmp = None
    if values['--mb1_bct'] is None:
        values['--mb1_bct'] = 'mb1_bct.cfg'
    tmp = values['--mb1_bct']

    if bool(is_cold_boot_mb1_bct) == True:
        if values['--mb1_cold_boot_bct'] is None:
            values['--mb1_cold_boot_bct'] = 'mb1_cold_boot_bct.cfg'
        tmp = values['--mb1_cold_boot_bct']

    if tmp is not None:
        command.extend(['--mb1bct', tmp])

    if int(values['--chip'], 0) in [0x19, 0x23]:
        concatenate_misc_cfg()

    command.extend(['--sdram', values['--sdram_config']])

    tmp = None
    if values['--misc_config'] is not None:
        tmp = values['--misc_config']
    if bool(is_cold_boot_mb1_bct) == True:
        if values['--misc_cold_boot_config'] is not None:
            tmp = values['--misc_cold_boot_config']
    if tmp is not None:
        command.extend(['--misc', tmp])

    tmp = None
    if values['--scr_config'] is not None:
        tmp = values['--scr_config']
    if bool(is_cold_boot_mb1_bct) == True:
        if values['--scr_cold_boot_config'] is not None:
            tmp = values['--scr_cold_boot_config']
    if tmp is not None:
        command.extend(['--scr', tmp])

    if values['--wb0sdram_config'] is not None:
        command.extend(['--wb0sdram', values['--wb0sdram_config']])
    if values['--pinmux_config'] is not None:
        command.extend(['--pinmux', values['--pinmux_config']])
    if values['--pmc_config'] is not None:
        command.extend(['--pmc', values['--pmc_config']])
    if values['--pmic_config'] is not None:
        command.extend(['--pmic', values['--pmic_config']])
    if values['--br_cmd_config'] is not None:
        command.extend(['--brcommand', values['--br_cmd_config']])
    if values['--prod_config'] is not None:
        command.extend(['--prod', values['--prod_config']])
    if int(values['--chip'], 0) in [0x19, 0x23]:
        if values['--gpioint_config'] is not None:
            command.extend(['--gpioint', values['--gpioint_config']])
        if values['--uphy_config'] is not None:
            command.extend(['--uphy', values['--uphy_config']])
        if values['--device_config'] is not None:
            command.extend(['--device', values['--device_config']])
        if values['--deviceprod_config'] is not None:
            command.extend(['--deviceprod', values['--deviceprod_config']])
        if values['--fb'] is not None:
            command.extend(['--fb', values['--fb']])

    run_command(command)

    if bool(is_cold_boot_mb1_bct) == True:
        tegrabct_values['--mb1_cold_boot_bct'] = os.path.splitext(values['--mb1_cold_boot_bct'])[0] + '_MB1.bct'
        mb1bct_file = tegrabct_values['--mb1_cold_boot_bct']
    else:
        tegrabct_values['--mb1_bct'] = os.path.splitext(values['--mb1_bct'])[0] + '_MB1.bct'
        mb1bct_file = tegrabct_values['--mb1_bct']

    if tegraparser_values['--pt'] is not None:
        info_print('Updating mb1-bct with firmware information')
        command = exec_file('tegrabct')
        command.extend(['--chip', values['--chip']])
        command.extend(['--mb1bct', mb1bct_file])
        command.extend(['--updatefwinfo', tegraparser_values['--pt']])
        run_command(command)

        info_print('Updating mb1-bct with storage information')
        command = exec_file('tegrabct')
        command.extend(['--chip', values['--chip']])
        command.extend(['--mb1bct', mb1bct_file])
        command.extend(['--updatestorageinfo', tegraparser_values['--pt']])
        run_command(command)

    if values['--minratchet_config'] is not None:
        info_print('Updating mb1-bct with ratchet information')
        command = exec_file('tegrabct')
        command.extend(['--chip', values['--chip']])
        command.extend(['--mb1bct', mb1bct_file])
        command.extend(['--minratchet', values['--minratchet_config']])
        run_command(command)

    if bool(is_cold_boot_mb1_bct) == True:
        if values['--encrypt_key'] is not None:
            tegrabct_values['--mb1_cold_boot_bct'] = tegraflash_oem_encrypt_and_sign_file(tegrabct_values['--mb1_cold_boot_bct'] ,True, 'MBCT')
            tegrabct_values['--mb1_cold_boot_bct'] = tegraflash_oem_encrypt_and_sign_file(tegrabct_values['--mb1_cold_boot_bct'] ,False,'MBCT')
        else:
            tegrabct_values['--mb1_cold_boot_bct'] = tegraflas_oem_sign_file(tegrabct_values['--mb1_cold_boot_bct'], 'MBCT')
    else:
        if values['--encrypt_key'] is not None:
            tegrabct_values['--mb1_bct'] = tegraflash_oem_encrypt_and_sign_file(tegrabct_values['--mb1_bct'] ,True, 'MBCT')
            tegrabct_values['--mb1_bct'] = tegraflash_oem_encrypt_and_sign_file(tegrabct_values['--mb1_bct'] ,False, 'MBCT')
        else:
            tegrabct_values['--mb1_bct'] = tegraflas_oem_sign_file(tegrabct_values['--mb1_bct'], 'MBCT')

def tegraflash_generate_bct():
    if values['--external_device']:
        # Don't generate bct for external devices
        return

    tegraflash_generate_br_bct(True)

    if int(values['--chip'], 0) == 0x21 and int(values['--chip_major'], 0) > 1:
        tegraflash_generate_br_bct(False)

    if values['--tegraflash_v2']:
       tegraflash_generate_mb1_bct(True) # generates coldboot mb1-bct
       tegraflash_generate_mb1_bct(False) # generates recovery mb1-bct
       tegraflash_generate_mem_bct(True)
       tegraflash_generate_mem_bct(False)

def tegraflash_parse_partitionlayout():
    info_print('Parsing partition layout')
    command = exec_file('tegraparser')
    command.extend(['--pt', values['--cfg']])
    tegraparser_values['--pt'] = os.path.splitext(values['--cfg'])[0] + '.bin'
    # print (tegraparser_values['--pt'])
    run_command(command)

def tegraflash_generate_rcm_message(is_pdf = False):
    info_print('Generating RCM messages')
    soft_fuse_bin = None

    command = exec_file('tegrarcm')
    command.extend(['--listrcm', tegrarcm_values['--list']])
    command.extend(['--chip', values['--chip'], values['--chip_major']])
    command.extend(['--download', 'rcm', values['--applet'], '0', '0'])

    run_command(command)

    info_print('Signing RCM messages')
    command = exec_file('tegrasign')
    command.extend(['--key'] + values['--key'])
    command.extend(['--list', tegrarcm_values['--list']])
    command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])
    if int(values['--chip'], 0) in [0x19, 0x23]:
        command.extend(['--getmontgomeryvalues', tegrasign_values['--getmontgomeryvalues']])
    run_command(command)

    info_print('Copying signature to RCM mesages')
    command = exec_file('tegrarcm')
    command.extend(['--chip', values['--chip'], values['--chip_major']])
    command.extend(['--updatesig', tegrarcm_values['--signed_list']])

    if os.path.isfile(tegrasign_values['--pubkeyhash']):
        command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])

    if os.path.exists(tegrasign_values['--getmontgomeryvalues']):
        command.extend(['--setmontgomeryvalues', tegrasign_values['--getmontgomeryvalues']])
    run_command(command)
    # print("done generating rcm message")

def tegraflash_update_img_path(cfg_file):
    if os.path.isfile(cfg_file) is False:
        return cfg_file

    with open(cfg_file, 'r+') as file:
        xml_tree = ElementTree.parse(file)

    root = xml_tree.getroot()

    for fname in root.findall('.//filename'):
        if fname.text and os.path.split(fname.text)[0]:
            fname.text = fname.text.lstrip()
            fname.text = fname.text.rstrip()
            img_path = fname.text
            fname.text = os.path.basename(fname.text)
            tegraflash_symlink(tegraflash_abs_path(img_path), paths['TMP'] + '/' + fname.text)
            fname.text = ' ' + fname.text + ' '

    new_cfg_file = os.path.basename(cfg_file) + '.tmp'
    with open(new_cfg_file, 'w+') as file:
        xml_tree.write(new_cfg_file)
        return new_cfg_file

    return cfg_file

def tegraflash_ufs_otp(args, otp_args):
    values.update(args)
    if int(values['--chip'], 0) == 0x21: # Bypass for t210
        return
    filename = os.path.basename(otp_args[0])
    if not os.path.exists(filename):
        raise tegraflash_exception('Could not find ' + otp_args[0])
    filename = os.path.splitext(otp_args[0])
    if filename[1] != '.xml':
        raise tegraflash_exception(otp_args[0] + ' is not an xml file')

    if values['--securedev']:
        tegraflash_send_tboot(args['--applet'])
    else:
        tegraflash_generate_rcm_message()
        tegraflash_send_tboot(tegrarcm_values['--signed_list'])
    args['--skipuid'] = False

    compulsory_args = ['--bl', '--sdram_config']
    for required_arg in compulsory_args:
        if args[required_arg] is None:
            args[required_arg] = input('Input ' + required_arg + ': ')

    tegraflash_get_key_mode()
    tegraflash_generate_bct()
    tegraflash_send_bct()
    tegraflash_send_bootloader()
    tegraflash_boot('recovery')

    info_print('Starting configure UFS')
    command = exec_file('tegradevflash')
    if otp_args[0] == 'dummy':
        command.extend(['--oem', 'ufsotp', otp_args[0] ])
    else:
        info_print('Parsing UFS configuration data as per xml file')
        command = exec_file('tegraparser')
        command.extend(['--ufs_otp', otp_args[0], tegraparser_values['--ufs_otp']])
        run_command(command)

        command = exec_file('tegradevflash')
        command.extend(['--oem', 'ufsotp'])
        command.extend([tegraparser_values['--ufs_otp']])

    run_command(command)

if __name__ == '__main__':
    tegraflash_sign()