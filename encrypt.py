import os
import sys
import tegraflash_internal

from tegraflash_internal import cmd_environ, paths, tegraflash_update_img_path
from tegraflash_internal import tegraflash_exception, tegraflash_os_path, tegraflash_abs_path
from tegraflash_internal import tegraflash_mkdevimages, tegraflash_flash, tegraflash_sign, tegraflash_encrypt_and_sign
from tegraflash_internal import tegraflash_test, tegraflash_read, tegraflash_write, tegraflash_erase, tegraflash_setverify, tegraflash_verify
from tegraflash_internal import tegraflash_ccgupdate, tegraflash_packageccg
from tegraflash_internal import tegraflash_parse, tegraflash_reboot, tegraflash_dump
from tegraflash_internal import tegraflash_rcmbl, tegraflash_rcmboot, tegraflash_encrypt_sign_binary
from tegraflash_internal import tegraflash_burnfuses, tegraflash_readfuses, tegraflash_blowfuses
from tegraflash_internal import tegraflash_provision_rollback, tegraflash_readmrr, tegraflash_symlink
from tegraflash_internal import tegraflash_secureflash, tegraflash_signwrite, tegraflash_nvsign
from tegraflash_internal import tegraflash_flush_sata, tegraflash_sata_fwdownload
from tegraflash_internal import tegraflash_ufs_otp, tegraflash_generate_recovery_blob
from tegraflash_internal import tegraflash_update_rpmb

def encrypt():
    tegraflash_internal.cmd_environ = os.environ.copy()
    tegraflash_internal.paths = {'OUT':None, 'BIN':None, 'SCRIPT':None, 'TMP':None, 'WD':os.getcwd()}
    tegraflash_internal.cmd_environ["PATH"] = '/Linux_for_Tegra/bootloader'

    if sys.argv[1] == 'jetson-nano':
        exports = {'--bct': 'P3448_A00_lpddr4_204Mhz_P987.cfg', '--bct_cold_boot': None, '--key': ['None'], '--encrypt_key': None, '--cfg': 'flash.xml.tmp', '--bl': 'cboot.bin', '--board': None, '--eeprom': None, '--cmd': 'sign; write DTB ./signed/kernel_tegra210-p3448-0002-p3449-0000-b00.dtb.encrypt; reboot', '--instance': None, '--bpfdtb': None, '--hostbin': None, '--applet': 'nvtboot_recovery.bin', '--dtb': None, '--bldtb': 'kernel_tegra210-p3448-0002-p3449-0000-b00.dtb', '--kerneldtb': None, '--chip': '0x21', '--out': None, '--nct': None, '--fb': None, '--odmdata': '0xa4000', '--lnx': None, '--tos': None, '--eks': None, '--boardconfig': None, '--skipuid': False, '--securedev': False, '--keyindex': None, '--keep': False, '--wb': None, '--bl-load': None, '--bins': None, '--dev_params': None, '--sdram_config': None, '--ramcode': None, '--misc_config': None, '--misc_cold_boot_config': None, '--pinmux_config': None, '--pmc_config': None, '--pmic_config': None, '--gpioint_config': None, '--uphy_config': None, '--scr_config': None, '--scr_cold_boot_config': None, '--br_cmd_config': None, '--prod_config': None, '--device_config': None, '--applet-cpu': None, '--bpf': None, '--mb1_bct': None, '--mb1_cold_boot_bct': None, '--skipsanitize': False, '--tegraflash_v2': False, '--chip_major': '0', '--nv_key': None, '--nvencrypt_key': None, '--cl': '39314184', '--soft_fuses': None, '--deviceprod_config': None, '--rcm_bct': 'P3448_A00_lpddr4_204Mhz_P987.cfg', '--secureboot': False, '--mem_bct': None, '--mem_bct_cold_boot': None, '--minratchet_config': None, '--wb0sdram_config': None, '--blversion': None, '--ratchet_blob': None, '--output_dir': None, '--applet_softfuse': None, '--ignorebfs': None, '--trim_bpmp_dtb': False, '--external_device': False}
        tegraflash_sign(exports)

if __name__ == "__main__":
    encrypt()
