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

def tegraflash_sign(exports):
    values.update(exports)
    cfg_file = values['--cfg']
    signed_files = [ ]

    command = exec_file('tegrasign')
    command.extend(['--key'] + values['--key'])
    command.extend(['--getmode', 'mode.txt'])
    run_command(command)

    with open('mode.txt') as mode_file:
        tegrasign_values['--mode'] = mode_file.read()

    output_dir = tegraflash_abs_path('signed')
    os.makedirs(output_dir)

    images_to_sign = ['mts_preboot', 'mts_bootpack', 'mts_mce', 'mts_proper', 'mb2_bootloader', 'fusebypass', 'bootloader_dtb', 'spe_fw', 'bpmp_fw', 'bpmp_fw_dtb', 'tlk', 'eks', 'dtb', 'ebt', 'tbc']
    binaries = []
    tegraflash_generate_rcm_message()

    if values['--cfg'] is not None :
        tegraflash_parse_partitionlayout()
        tegraflash_sign_images()
        tegraflash_generate_bct()
        tegraflash_update_images()
        tegraflash_update_bfs_images()
        # generate gpt and mbr
        # TODO: add T210 support
        if int(values['--chip'], 0) == 0x18 or int(values['--chip'], 0) == 0x19 :
            command = exec_file('tegraparser')
            command.extend(['--generategpt', '--pt', tegraparser_values['--pt']])
            run_command(command)
            import re
            patt = re.compile(".*(mbr|gpt).*\.bin")
            contents = os.listdir('.')
            for f in contents:
                if patt.match(f):
                    shutil.copyfile(f, output_dir + "/" + f)

    if values['--bins'] is not None:
        bins = values['--bins'].split(';')
        for binary in bins:
            binary = binary.strip(' ')
            binary = binary.replace('  ', ' ')
            tags = binary.split(' ')
            if (len(tags) < 2):
                raise tegraflash_exception('invalid format ' + binary)

            if tags[0] in images_to_sign:
                if int(values['--chip'], 0) == 0x21:
                   tags[0] = tags[0].upper()
                   tags[1] = tegraflash_t21x_sign_file(tags[0], tags[1])
                else:
                   magic_id = tegraflash_get_magicid(tags[0])
                   tags[1] = tegraflas_oem_sign_file(tags[1], magic_id)
                binaries.extend([tags[1]])

    if values['--tegraflash_v2'] and values['--bl']:
        values['--bl'] = tegraflas_oem_sign_file(values['--bl'], 'CPBL')
        binaries.extend([values['--bl']])

    info_print("Copying signed file in " + output_dir)
    signed_files.extend(tegraflash_copy_signed_binaries(tegrarcm_values['--signed_list'], output_dir))

    if values['--cfg'] is not None :
        signed_files.extend(tegraflash_copy_signed_binaries(tegrahost_values['--signed_list'], output_dir))
        shutil.copyfile(tegrabct_values['--bct'], output_dir + "/" + tegrabct_values['--bct'])
        if int(values['--chip'], 0) == 0x21 and int(values['--chip_major'], 0) > 1:
            shutil.copyfile(tegrabct_values['--rcm_bct'], output_dir + "/" + tegrabct_values['--rcm_bct'])
        tegraflash_update_cfg_file(signed_files, cfg_file, output_dir, int(values['--chip'], 0))

    if tegrabct_values['--mb1_bct'] is not None:
        shutil.copyfile(tegrabct_values['--mb1_bct'], output_dir + "/" + tegrabct_values['--mb1_bct'])
    if tegrabct_values['--mb1_cold_boot_bct'] is not None:
        shutil.copyfile(tegrabct_values['--mb1_cold_boot_bct'], output_dir + "/" + tegrabct_values['--mb1_cold_boot_bct'])

    if tegrabct_values['--membct_rcm'] is not None:
        shutil.copyfile(tegrabct_values['--membct_rcm'], output_dir + "/" + tegrabct_values['--membct_rcm'])
    if tegrabct_values['--membct_cold_boot'] is not None:
        shutil.copyfile(tegrabct_values['--membct_cold_boot'], output_dir + "/" + tegrabct_values['--membct_cold_boot'])

    for signed_binary in binaries:
        shutil.copyfile(signed_binary, output_dir + "/" + signed_binary)

    if tegraparser_values['--pt'] is not None:
        shutil.copyfile(tegraparser_values['--pt'], output_dir + "/" + tegraparser_values['--pt'])

    # generate flashing index file
    # TODO: add T210 support
    if int(values['--chip'], 0) == 0x18 or int(values['--chip'], 0) == 0x19 :
        # --pt flash.xml.bin --generateflashindex flash.xml.tmp <out>
        flash_index = "flash.idx"
        tegraflash_generate_index_file(output_dir + "/" + os.path.basename(cfg_file), flash_index)
        shutil.copyfile(flash_index, output_dir + "/" + flash_index)

def tegraflash_generate_rcm_message(is_pdf = False):
    info_print('Generating RCM messages')
    soft_fuse_bin = None

    if int(values['--chip'], 0) in [0x19, 0x23]:
        #update stage2 components
        mode = 'zerosbk'
        sig_type = 'zerosbk'
        filename = values['--applet']
        if values['--encrypt_key'] is not None:
            command = exec_file('tegrasign')
            command.extend(['--key'] + values['--encrypt_key'])
            command.extend(['--file', filename])
            command.extend(['--offset', '4096'])
            run_command(command)
            filename = os.path.splitext(filename)[0] + '_encrypt' + os.path.splitext(filename)[1]

        command = exec_file('tegrahost')
        command.extend(['--chip', values['--chip'], values['--chip_major']])
        command.extend(['--magicid', 'MB1B'])
        command.extend(['--appendsigheader', filename, mode])
        run_command(command)
        filename = os.path.splitext(filename)[0] + '_sigheader' + os.path.splitext(filename)[1]
        values['--applet'] = filename;

        tegraflash_get_key_mode()
        mode = tegrasign_values['--mode']
        filename = values['--applet']

        command = exec_file('tegrasign')
        command.extend(['--key'] + values['--key'])
        command.extend(['--file', filename])
        command.extend(['--offset', '2960'])
        command.extend(['--length', '1136'])
        command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])
        if mode == "pkc":
            command.extend(['--getmontgomeryvalues', tegrasign_values['--getmontgomeryvalues']])
        run_command(command)

        command = exec_file('tegrahost')
        command.extend(['--chip', values['--chip'], values['--chip_major']])
        if mode == "pkc":
            sig_type = "oem-rsa"
            command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])
            command.extend(['--setmontgomeryvalues', tegrasign_values['--getmontgomeryvalues']])
        signed_file = os.path.splitext(filename)[0] + '.sig'
        if mode == "ec":
            sig_type = "oem-ecc"
            command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])
        if mode == "zerosbk":
           signed_file = os.path.splitext(filename)[0] + '.hash'
           sig_type = "zerosbk"
        command.extend(['--updatesigheader', filename, signed_file, sig_type])
        run_command(command)
        values['--applet'] = filename

        if values['--soft_fuses'] is not None:
            soft_fuse_config = values['--soft_fuses']
            if is_pdf:
                shutil.copyfile(soft_fuse_config, soft_fuse_config + '.pdf')
                soft_fuse_config = soft_fuse_config + '.pdf'
                with open(soft_fuse_config, 'a+') as f:
                    f.write('\nPlatformDetectionFlow = 1;\n')

            soft_fuse_bin = 'sfuse.bin'
            command = exec_file('tegrabct')
            command.extend(['--chip', values['--chip'], values['--chip_major']])
            command.extend(['--sfuse', soft_fuse_config, soft_fuse_bin])
            run_command(command)

        if values['--minratchet_config'] is not None:
           command = exec_file('tegrabct')
           command.extend(['--chip', values['--chip'], values['--chip_major']])
           command.extend(['--ratchet_blob', tegrahost_values['--ratchet_blob']])
           command.extend(['--minratchet', values['--minratchet_config']])
           run_command(command)

    command = exec_file('tegrarcm')
    command.extend(['--listrcm', tegrarcm_values['--list']])
    command.extend(['--chip', values['--chip'], values['--chip_major']])

    if soft_fuse_bin is not None:
        command.extend(['--sfuses', soft_fuse_bin])

    if values['--keyindex'] is not None:
        command.extend(['--keyindex', values['--keyindex']])

    if int(values['--chip'], 0) == 0x13:
        command.extend(['--download', 'rcm', 'mts_preboot_si', '0x4000F000'])

    command.extend(['--download', 'rcm', values['--applet'], '0', '0'])
    run_command(command)

    if values['--encrypt_key'] is not None and int(values['--chip'], 0) == 0x18:
        info_print('Signing RCM messages')
        command = exec_file('tegrasign')
        command.extend(['--key', values['--encrypt_key'][0]])
        command.extend(['--list', tegrarcm_values['--list']])
        command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])
        run_command(command)

        info_print('Copying signature to RCM mesages')
        command = exec_file('tegrarcm')
        command.extend(['--chip', values['--chip']])
        command.extend(['--updatesig', tegrarcm_values['--signed_list']])
        os.remove('rcm_0.rcm')
        os.remove('rcm_1.rcm')
        os.rename('rcm_0_encrypt.rcm' , 'rcm_0.rcm')
        os.rename('rcm_1_encrypt.rcm' , 'rcm_1.rcm')

    info_print('Signing RCM messages')
    if not values['--tegraflash_v2'] and int(values['--chip_major'], 0) >= 2 and values['--encrypt_key'] is not None:
        with open(tegrarcm_values['--list'], 'r+') as file:
            xml_tree = ElementTree.parse(file)
            root = xml_tree.getroot()
            for child in root:
                child.find('sbk').set('encrypt', '1')
            xml_tree.write(tegrarcm_values['--list'])

        command = exec_file('tegrasign')
        command.extend(['--key', values['--encrypt_key'][-1]])
        command.extend(['--list', tegrarcm_values['--list']])
        command.extend(['--pubkeyhash', tegrasign_values['--pubkeyhash']])
        run_command(command)

        with open(tegrarcm_values['--list'], 'r+') as file:
            xml_tree = ElementTree.parse(file)
            root = xml_tree.getroot()
            for child in root:
                child.find('sbk').set('encrypt', '0')
                sbk_file = child.find('sbk').attrib.get('encrypt_file')
                child.set('name', sbk_file)
            xml_tree.write(tegrarcm_values['--list'])
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