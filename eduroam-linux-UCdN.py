#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 * **************************************************************************
 * Contributions to this work were made on behalf of the GÉANT project,
 * a project that has received funding from the European Union’s Framework
 * Programme 7 under Grant Agreements No. 238875 (GN3)
 * and No. 605243 (GN3plus), Horizon 2020 research and innovation programme
 * under Grant Agreements No. 691567 (GN4-1) and No. 731122 (GN4-2).
 * On behalf of the aforementioned projects, GEANT Association is
 * the sole owner of the copyright in all material which was developed
 * by a member of the GÉANT project.
 * GÉANT Vereniging (Association) is registered with the Chamber of
 * Commerce in Amsterdam with registration number 40535155 and operates
 * in the UK as a branch of GÉANT Vereniging.
 * 
 * Registered office: Hoekenrode 3, 1102BR Amsterdam, The Netherlands.
 * UK branch address: City House, 126-130 Hills Road, Cambridge CB2 1PQ, UK
 *
 * License: see the web/copyright.inc.php file in the file structure or
 *          <base_url>/copyright.php after deploying the software

Authors:
    Tomasz Wolniewicz <twoln@umk.pl>
    Michał Gasewicz <genn@umk.pl> (Network Manager support)

Contributors:
    Steffen Klemer https://github.com/sklemer1
    ikerb7 https://github.com/ikreb7
Many thanks for multiple code fixes, feature ideas, styling remarks
much of the code provided by them in the form of pull requests
has been incorporated into the final form of this script.

This script is the main body of the CAT Linux installer.
In the generation process configuration settings are added
as well as messages which are getting translated into the language
selected by the user.

The script is meant to run both under python 2.7 and python3. It tests
for the crucial dbus module and if it does not find it and if it is not
running python3 it will try rerunning iself again with python3.
"""
import argparse
import base64
import getpass
import os
import re
import subprocess
import sys
import uuid
from shutil import copyfile

NM_AVAILABLE = True
CRYPTO_AVAILABLE = True
DEBUG_ON = False
DEV_NULL = open("/dev/null", "w")
STDERR_REDIR = DEV_NULL


def debug(msg):
    """Print debugging messages to stdout"""
    if not DEBUG_ON:
        return
    print("DEBUG:" + str(msg))


def missing_dbus():
    """Handle missing dbus module"""
    global NM_AVAILABLE
    debug("Cannot import the dbus module")
    NM_AVAILABLE = False


def byte_to_string(barray):
    """conversion utility"""
    return "".join([chr(x) for x in barray])


def get_input(prompt):
    if sys.version_info.major < 3:
        return raw_input(prompt)
    return input(prompt)


debug(sys.version_info.major)


try:
    import dbus
except ImportError:
    if sys.version_info.major == 3:
        missing_dbus()
    if sys.version_info.major < 3:
        try:
            subprocess.call(['python3'] + sys.argv)
        except:
            missing_dbus()
        sys.exit(0)

try:
    from OpenSSL import crypto
except ImportError:
    CRYPTO_AVAILABLE = False


if sys.version_info.major == 3 and sys.version_info.minor >= 8:
    import distro
else:
    import platform


# the function below was partially copied
# from https://ubuntuforums.org/showthread.php?t=1139057
def detect_desktop_environment():
    """
    Detect what desktop type is used. This method is prepared for
    possible future use with password encryption on supported distros
    """
    desktop_environment = 'generic'
    if os.environ.get('KDE_FULL_SESSION') == 'true':
        desktop_environment = 'kde'
    elif os.environ.get('GNOME_DESKTOP_SESSION_ID'):
        desktop_environment = 'gnome'
    else:
        try:
            shell_command = subprocess.Popen(['xprop', '-root',
                                              '_DT_SAVE_MODE'],
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
            out, err = shell_command.communicate()
            info = out.decode('utf-8').strip()
        except (OSError, RuntimeError):
            pass
        else:
            if ' = "xfce4"' in info:
                desktop_environment = 'xfce'
    return desktop_environment


def get_system():
    """
    Detect Linux platform. Not used at this stage.
    It is meant to enable password encryption in distros
    that can handle this well.
    """
    if sys.version_info.major == 3 and sys.version_info.minor >= 8:
        system = distro.linux_distribution()
    else:
        system = platform.linux_distribution()
    desktop = detect_desktop_environment()
    return [system[0], system[1], desktop]


def run_installer():
    """
    This is the main installer part. It tests for MN availability
    gets user credentials and starts a proper installer.
    """
    global DEBUG_ON
    global NM_AVAILABLE
    username = ''
    password = ''
    silent = False
    pfx_file = ''
    parser = argparse.ArgumentParser(description='eduroam linux installer.')
    parser.add_argument('--debug', '-d', action='store_true', dest='debug',
                        default=False, help='set debug flag')
    parser.add_argument('--username', '-u', action='store', dest='username',
                        help='set username')
    parser.add_argument('--password', '-p', action='store', dest='password',
                        help='set text_mode flag')
    parser.add_argument('--silent', '-s', action='store_true', dest='silent',
                        help='set silent flag')
    parser.add_argument('--pfxfile', action='store', dest='pfx_file',
                        help='set path to user certificate file')
    args = parser.parse_args()
    if args.debug:
        DEBUG_ON = True
        print("Running debug mode")

    if args.username:
        username = args.username
    if args.password:
        password = args.password
    if args.silent:
        silent = args.silent
    if args.pfx_file:
        pfx_file = args.pfx_file
    debug(get_system())
    debug("Calling InstallerData")
    installer_data = InstallerData(silent=silent, username=username,
                                   password=password, pfx_file=pfx_file)

    # test dbus connection
    if NM_AVAILABLE:
        config_tool = CatNMConfigTool()
        if config_tool.connect_to_nm() is None:
            NM_AVAILABLE = False
    if not NM_AVAILABLE:
        # no dbus so ask if the user will want wpa_supplicant config
        if installer_data.ask(Messages.save_wpa_conf, Messages.cont, 1):
            sys.exit(1)
    installer_data.get_user_cred()
    installer_data.save_ca()
    if NM_AVAILABLE:
        config_tool.add_connections(installer_data)
    else:
        wpa_config = WpaConf()
        wpa_config.create_wpa_conf(Config.ssids, installer_data)
    installer_data.show_info(Messages.installation_finished)


class Messages(object):
    """
    These are initial definitions of messages, but they will be
    overridden with translated strings.
    """
    quit = "Really quit?"
    username_prompt = "enter your userid"
    enter_password = "enter password"
    enter_import_password = "enter your import password"
    incorrect_password = "incorrect password"
    repeat_password = "repeat your password"
    passwords_difffer = "passwords do not match"
    installation_finished = "Installation successful"
    cat_dir_exists = "Directory {} exists; some of its files may be " \
        "overwritten."
    cont = "Continue?"
    nm_not_supported = "This NetworkManager version is not supported"
    cert_error = "Certificate file not found, looks like a CAT error"
    unknown_version = "Unknown version"
    dbus_error = "DBus connection problem, a sudo might help"
    yes = "Y"
    nay = "N"
    p12_filter = "personal certificate file (p12 or pfx)"
    all_filter = "All files"
    p12_title = "personal certificate file (p12 or pfx)"
    save_wpa_conf = "NetworkManager configuration failed, " \
        "but we may generate a wpa_supplicant configuration file " \
        "if you wish. Be warned that your connection password will be saved " \
        "in this file as clear text."
    save_wpa_confirm = "Write the file"
    wrongUsernameFormat = "Error: Your username must be of the form " \
        "'xxx@institutionID' e.g. 'john@example.net'!"
    wrong_realm = "Error: your username must be in the form of 'xxx@{}'. " \
        "Please enter the username in the correct format."
    wrong_realm_suffix = "Error: your username must be in the form of " \
        "'xxx@institutionID' and end with '{}'. Please enter the username " \
        "in the correct format."
    user_cert_missing = "personal certificate file not found"
    # "File %s exists; it will be overwritten."
    # "Output written to %s"


class Config(object):
    """
    This is used to prepare settings during installer generation.
    """
    instname = ""
    profilename = ""
    url = ""
    email = ""
    title = "eduroam CAT"
    servers = []
    ssids = []
    del_ssids = []
    eap_outer = ''
    eap_inner = ''
    use_other_tls_id = False
    server_match = ''
    anonymous_identity = ''
    CA = ""
    init_info = ""
    init_confirmation = ""
    tou = ""
    sb_user_file = ""
    verify_user_realm_input = False
    user_realm = ""
    hint_user_input = False


class InstallerData(object):
    """
    General user interaction handling, supports zenity, kdialog and
    standard command-line interface
    """

    def __init__(self, silent=False, username='', password='', pfx_file=''):
        self.graphics = ''
        self.username = username
        self.password = password
        self.silent = silent
        self.pfx_file = pfx_file
        debug("starting constructor")
        if silent:
            self.graphics = 'tty'
        else:
            self.__get_graphics_support()
        self.show_info(Config.init_info.format(Config.instname,
                                               Config.email, Config.url))
        if self.ask(Config.init_confirmation.format(Config.instname,
                                                    Config.profilename),
                    Messages.cont, 1):
            sys.exit(1)
        if Config.tou != '':
            if self.ask(Config.tou, Messages.cont, 1):
                sys.exit(1)
        if os.path.exists(os.environ.get('HOME') + '/.cat_installer'):
            if self.ask(Messages.cat_dir_exists.format(
                    os.environ.get('HOME') + '/.cat_installer'),
                        Messages.cont, 1):
                sys.exit(1)
        else:
            os.mkdir(os.environ.get('HOME') + '/.cat_installer', 0o700)

    def save_ca(self):
        """
        Save CA certificate to .cat_installer directory
        (create directory if needed)
        """
        certfile = os.environ.get('HOME') + '/.cat_installer/ca.pem'
        debug("saving cert")
        with open(certfile, 'w') as cert:
            cert.write(Config.CA + "\n")

    def ask(self, question, prompt='', default=None):
        """
        Propmpt user for a Y/N reply, possibly supplying a default answer
        """
        if self.silent:
            return 0
        if self.graphics == 'tty':
            yes = Messages.yes[:1].upper()
            nay = Messages.nay[:1].upper()
            print("\n-------\n" + question + "\n")
            while True:
                tmp = prompt + " (" + Messages.yes + "/" + Messages.nay + ") "
                if default == 1:
                    tmp += "[" + yes + "]"
                elif default == 0:
                    tmp += "[" + nay + "]"
                inp = get_input(tmp)
                if inp == '':
                    if default == 1:
                        return 0
                    if default == 0:
                        return 1
                i = inp[:1].upper()
                if i == yes:
                    return 0
                if i == nay:
                    return 1
        if self.graphics == "zenity":
            command = ['zenity', '--title=' + Config.title, '--width=500',
                       '--question', '--text=' + question + "\n\n" + prompt]
        elif self.graphics == 'kdialog':
            command = ['kdialog', '--yesno', question + "\n\n" + prompt,
                       '--title=', Config.title]
        returncode = subprocess.call(command, stderr=STDERR_REDIR)
        return returncode

    def show_info(self, data):
        """
        Show a piece of information
        """
        if self.silent:
            return
        if self.graphics == 'tty':
            print(data)
            return
        if self.graphics == "zenity":
            command = ['zenity', '--info', '--width=500', '--text=' + data]
        elif self.graphics == "kdialog":
            command = ['kdialog', '--msgbox', data]
        else:
            sys.exit(1)
        subprocess.call(command, stderr=STDERR_REDIR)

    def confirm_exit(self):
        """
        Confirm exit from installer
        """
        ret = self.ask(Messages.quit)
        if ret == 0:
            sys.exit(1)

    def alert(self, text):
        """Generate alert message"""
        if self.silent:
            return
        if self.graphics == 'tty':
            print(text)
            return
        if self.graphics == 'zenity':
            command = ['zenity', '--warning', '--text=' + text]
        elif self.graphics == "kdialog":
            command = ['kdialog', '--sorry', text]
        else:
            sys.exit(1)
        subprocess.call(command, stderr=STDERR_REDIR)

    def prompt_nonempty_string(self, show, prompt, val=''):
        """
        Prompt user for input
        """
        if self.graphics == 'tty':
            if show == 0:
                while True:
                    inp = str(getpass.getpass(prompt + ": "))
                    output = inp.strip()
                    if output != '':
                        return output
            while True:
                inp = str(get_input(prompt + ": "))
                output = inp.strip()
                if output != '':
                    return output

        if self.graphics == 'zenity':
            if val == '':
                default_val = ''
            else:
                default_val = '--entry-text=' + val
            if show == 0:
                hide_text = '--hide-text'
            else:
                hide_text = ''
            command = ['zenity', '--entry', hide_text, default_val,
                       '--width=500', '--text=' + prompt]
        elif self.graphics == 'kdialog':
            if show == 0:
                hide_text = '--password'
            else:
                hide_text = '--inputbox'
            command = ['kdialog', hide_text, prompt]

        output = ''
        while not output:
            shell_command = subprocess.Popen(command, stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
            out, err = shell_command.communicate()
            output = out.decode('utf-8').strip()
            if shell_command.returncode == 1:
                self.confirm_exit()
        return output

    def get_user_cred(self):
        """
        Get user credentials both username/password and personal certificate
        based
        """
        if Config.eap_outer == 'PEAP' or Config.eap_outer == 'TTLS':
            self.__get_username_password()
        if Config.eap_outer == 'TLS':
            self.__get_p12_cred()

    def __get_username_password(self):
        """
        read user password and set the password property
        do nothing if silent mode is set
        """
        password = "a"
        password1 = "b"
        if self.silent:
            return
        if self.username:
            user_prompt = self.username
        elif Config.hint_user_input:
            user_prompt = '@' + Config.user_realm
        else:
            user_prompt = ''
        while True:
            self.username = self.prompt_nonempty_string(
                1, Messages.username_prompt, user_prompt)
            if self.__validate_user_name():
                break
        while password != password1:
            password = self.prompt_nonempty_string(
                0, Messages.enter_password)
            password1 = self.prompt_nonempty_string(
                0, Messages.repeat_password)
            if password != password1:
                self.alert(Messages.passwords_difffer)
        self.password = password

    def __get_graphics_support(self):
        if os.environ.get('DISPLAY') is not None:
            shell_command = subprocess.Popen(['which', 'zenity'],
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
            shell_command.wait()
            if shell_command.returncode == 0:
                self.graphics = 'zenity'
            else:
                shell_command = subprocess.Popen(['which', 'kdialog'],
                                                 stdout=subprocess.PIPE,
                                                 stderr=subprocess.PIPE)
                shell_command.wait()
                # out, err = shell_command.communicate()
                if shell_command.returncode == 0:
                    self.graphics = 'kdialog'
                else:
                    self.graphics = 'tty'
        else:
            self.graphics = 'tty'

    def __process_p12(self):
        debug('process_p12')
        pfx_file = os.environ['HOME'] + '/.cat_installer/user.p12'
        if CRYPTO_AVAILABLE:
            debug("using crypto")
            try:
                p12 = crypto.load_pkcs12(open(pfx_file, 'rb').read(),
                                         self.password)
            except:
                debug("incorrect password")
                return False
            else:
                if Config.use_other_tls_id:
                    return True
                try:
                    self.username = p12.get_certificate().\
                        get_subject().commonName
                except:
                    self.username = p12.get_certificate().\
                        get_subject().emailAddress
                return True
        else:
            debug("using openssl")
            command = ['openssl', 'pkcs12', '-in', pfx_file, '-passin',
                       'pass:' + self.password, '-nokeys', '-clcerts']
            shell_command = subprocess.Popen(command, stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
            out, err = shell_command.communicate()
            if shell_command.returncode != 0:
                return False
            if Config.use_other_tls_id:
                return True
            out_str = out.decode('utf-8').strip()
            subject = re.split(r'\s*[/,]\s*',
                               re.findall(r'subject=/?(.*)$',
                                          out_str, re.MULTILINE)[0])
            cert_prop = {}
            for field in subject:
                if field:
                    cert_field = re.split(r'\s*=\s*', field)
                    cert_prop[cert_field[0].lower()] = cert_field[1]
            if cert_prop['cn'] and re.search(r'@', cert_prop['cn']):
                debug('Using cn: ' + cert_prop['cn'])
                self.username = cert_prop['cn']
            elif cert_prop['emailaddress'] and \
                    re.search(r'@', cert_prop['emailaddress']):
                debug('Using email: ' + cert_prop['emailaddress'])
                self.username = cert_prop['emailaddress']
            else:
                self.username = ''
                self.alert("Unable to extract username "
                           "from the certificate")
            return True

    def __select_p12_file(self):
        """
        prompt user for the PFX file selection
        this method is not being called in the silent mode
        therefore there is no code for this case
        """
        if self.graphics == 'tty':
            my_dir = os.listdir(".")
            p_count = 0
            pfx_file = ''
            for my_file in my_dir:
                if my_file.endswith('.p12') or my_file.endswith('*.pfx') or \
                        my_file.endswith('.P12') or my_file.endswith('*.PFX'):
                    p_count += 1
                    pfx_file = my_file
            prompt = "personal certificate file (p12 or pfx)"
            default = ''
            if p_count == 1:
                default = '[' + pfx_file + ']'

            while True:
                inp = get_input(prompt + default + ": ")
                output = inp.strip()

                if default != '' and output == '':
                    return pfx_file
                default = ''
                if os.path.isfile(output):
                    return output
                print("file not found")

        if self.graphics == 'zenity':
            command = ['zenity', '--file-selection',
                       '--file-filter=' + Messages.p12_filter +
                       ' | *.p12 *.P12 *.pfx *.PFX', '--file-filter=' +
                       Messages.all_filter + ' | *',
                       '--title=' + Messages.p12_title]
            shell_command = subprocess.Popen(command, stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
            cert, err = shell_command.communicate()
        if self.graphics == 'kdialog':
            command = ['kdialog', '--getopenfilename',
                       '.', '*.p12 *.P12 *.pfx *.PFX | ' +
                       Messages.p12_filter, '--title', Messages.p12_title]
            shell_command = subprocess.Popen(command, stdout=subprocess.PIPE,
                                             stderr=STDERR_REDIR)
            cert, err = shell_command.communicate()
        return cert.decode('utf-8').strip()

    def __save_sb_pfx(self):
        """write the user PFX file"""
        certfile = os.environ.get('HOME') + '/.cat_installer/user.p12'
        with open(certfile, 'wb') as cert:
            cert.write(base64.b64decode(Config.sb_user_file))

    def __get_p12_cred(self):
        """get the password for the PFX file"""
        if Config.eap_inner == 'SILVERBULLET':
            self.__save_sb_pfx()
        else:
            if self.silent:
                pfx_file = self.pfx_file
            else:
                pfx_file = self.__select_p12_file()
                try:
                    copyfile(pfx_file, os.environ['HOME'] +
                             '/.cat_installer/user.p12')
                except (OSError, RuntimeError):
                    print(Messages.user_cert_missing)
                    sys.exit(1)
        if self.silent:
            username = self.username
            if not self.__process_p12():
                sys.exit(1)
            if username:
                self.username = username
        else:
            while not self.password:
                self.password = self.prompt_nonempty_string(
                    0, Messages.enter_import_password)
                if not self.__process_p12():
                    self.alert(Messages.incorrect_password)
                    self.password = ''
            if not self.username:
                self.username = self.prompt_nonempty_string(
                    1, Messages.username_prompt)

    def __validate_user_name(self):
        # locate the @ character in username
        pos = self.username.find('@')
        debug("@ position: " + str(pos))
        # trailing @
        if pos == len(self.username) - 1:
            debug("username ending with @")
            self.alert(Messages.wrongUsernameFormat)
            return False
        # no @ at all
        if pos == -1:
            if Config.verify_user_realm_input:
                debug("missing realm")
                self.alert(Messages.wrongUsernameFormat)
                return False
            debug("No realm, but possibly correct")
            return True
        # @ at the beginning
        if pos == 0:
            debug("missing user part")
            self.alert(Messages.wrongUsernameFormat)
            return False
        pos += 1
        if Config.verify_user_realm_input:
            if Config.hint_user_input:
                if self.username.endswith('@' + Config.user_realm, pos-1):
                    debug("realm equal to the expected value")
                    return True
                debug("incorrect realm; expected:" + Config.user_realm)
                self.alert(Messages.wrong_realm.format(Config.user_realm))
                return False
            if self.username.endswith(Config.user_realm, pos):
                debug("realm ends with expected suffix")
                return True
            debug("realm suffix error; expected: " + Config.user_realm)
            self.alert(Messages.wrong_realm_suffix.format(
                Config.user_realm))
            return False
        pos1 = self.username.find('@', pos)
        if pos1 > -1:
            debug("second @ character found")
            self.alert(Messages.wrongUsernameFormat)
            return False
        pos1 = self.username.find('.', pos)
        if pos1 == pos:
            debug("a dot immediately after the @ character")
            self.alert(Messages.wrongUsernameFormat)
            return False
        debug("all passed")
        return True


class WpaConf(object):
    """
    Prepare and save wpa_supplicant config file
    """
    def __prepare_network_block(self, ssid, user_data):
        altsubj_match = "altsubject_match=\"%s\"" % ";".join(Config.servers)
        out = """network={
        ssid=""" + ssid + """
        key_mgmt=WPA-EAP
        pairwise=CCMP
        group=CCMP TKIP
        eap=""" + Config.eap_outer + """
        ca_cert=\"""" + os.environ.get('HOME') + """/.cat_installer/ca.pem\"
        identity=\"""" + user_data.username + """\"
        altsubject_match=\"""" + altsubj_match + """\"
        phase2=\"auth=""" + Config.eap_inner + """\"
        password=\"""" + user_data.password + """\"
        anonymous_identity=\"""" + Config.anonymous_identity + """\"
}
    """
        return out

    def create_wpa_conf(self, ssids, user_data):
        """Create and save the wpa_supplicant config file"""
        wpa_conf = os.environ.get('HOME') + \
            '/.cat_installer/cat_installer.conf'
        with open(wpa_conf, 'w') as conf:
            for ssid in ssids:
                net = self.__prepare_network_block(ssid, user_data)
                conf.write(net)


class CatNMConfigTool(object):
    """
    Prepare and save NetworkManager configuration
    """
    def __init__(self):
        self.cacert_file = None
        self.settings_service_name = None
        self.connection_interface_name = None
        self.system_service_name = None
        self.nm_version = None
        self.pfx_file = None
        self.settings = None
        self.user_data = None
        self.bus = None

    def connect_to_nm(self):
        """
        connect to DBus
        """
        try:
            self.bus = dbus.SystemBus()
        except dbus.exceptions.DBusException:
            print("Can't connect to DBus")
            return None
        # main service name
        self.system_service_name = "org.freedesktop.NetworkManager"
        # check NM version
        self.__check_nm_version()
        debug("NM version: " + self.nm_version)
        if self.nm_version == "0.9" or self.nm_version == "1.0":
            self.settings_service_name = self.system_service_name
            self.connection_interface_name = \
                "org.freedesktop.NetworkManager.Settings.Connection"
            # settings proxy
            sysproxy = self.bus.get_object(
                self.settings_service_name,
                "/org/freedesktop/NetworkManager/Settings")
            # settings interface
            self.settings = dbus.Interface(sysproxy, "org.freedesktop."
                                           "NetworkManager.Settings")
        elif self.nm_version == "0.8":
            self.settings_service_name = "org.freedesktop.NetworkManager"
            self.connection_interface_name = "org.freedesktop.NetworkMana" \
                                             "gerSettings.Connection"
            # settings proxy
            sysproxy = self.bus.get_object(
                self.settings_service_name,
                "/org/freedesktop/NetworkManagerSettings")
            # settings intrface
            self.settings = dbus.Interface(
                sysproxy, "org.freedesktop.NetworkManagerSettings")
        else:
            print(Messages.nm_not_supported)
            return None
        debug("NM connection worked")
        return True

    def __check_opts(self):
        """
        set certificate files paths and test for existence of the CA cert
        """
        self.cacert_file = os.environ['HOME'] + '/.cat_installer/ca.pem'
        self.pfx_file = os.environ['HOME'] + '/.cat_installer/user.p12'
        if not os.path.isfile(self.cacert_file):
            print(Messages.cert_error)
            sys.exit(2)

    def __check_nm_version(self):
        """
        Get the NetworkManager version
        """
        try:
            proxy = self.bus.get_object(
                self.system_service_name, "/org/freedesktop/NetworkManager")
            props = dbus.Interface(proxy, "org.freedesktop.DBus.Properties")
            version = props.Get("org.freedesktop.NetworkManager", "Version")
        except dbus.exceptions.DBusException:
            version = "0.8"
        if re.match(r'^1\.', version):
            self.nm_version = "1.0"
            return
        if re.match(r'^0\.9', version):
            self.nm_version = "0.9"
            return
        if re.match(r'^0\.8', version):
            self.nm_version = "0.8"
            return
        self.nm_version = Messages.unknown_version

    def __delete_existing_connection(self, ssid):
        """
        checks and deletes earlier connection
        """
        try:
            conns = self.settings.ListConnections()
        except dbus.exceptions.DBusException:
            print(Messages.dbus_error)
            exit(3)
        for each in conns:
            con_proxy = self.bus.get_object(self.system_service_name, each)
            connection = dbus.Interface(
                con_proxy,
                "org.freedesktop.NetworkManager.Settings.Connection")
            try:
                connection_settings = connection.GetSettings()
                if connection_settings['connection']['type'] == '802-11-' \
                                                                'wireless':
                    conn_ssid = byte_to_string(
                        connection_settings['802-11-wireless']['ssid'])
                    if conn_ssid == ssid:
                        debug("deleting connection: " + conn_ssid)
                        connection.Delete()
            except dbus.exceptions.DBusException:
                pass

    def __add_connection(self, ssid):
        debug("Adding connection: " + ssid)
        server_alt_subject_name_list = dbus.Array(Config.servers)
        server_name = Config.server_match
        if self.nm_version == "0.9" or self.nm_version == "1.0":
            match_key = 'altsubject-matches'
            match_value = server_alt_subject_name_list
        else:
            match_key = 'subject-match'
            match_value = server_name
        s_8021x_data = {
            'eap': [Config.eap_outer.lower()],
            'identity': self.user_data.username,
            'ca-cert': dbus.ByteArray(
                "file://{0}\0".format(self.cacert_file).encode('utf8')),
            match_key: match_value}
        if Config.eap_outer == 'PEAP' or Config.eap_outer == 'TTLS':
            s_8021x_data['password'] = self.user_data.password
            s_8021x_data['phase2-auth'] = Config.eap_inner.lower()
            if Config.anonymous_identity != '':
                s_8021x_data['anonymous-identity'] = Config.anonymous_identity
            s_8021x_data['password-flags'] = 0
        if Config.eap_outer == 'TLS':
            s_8021x_data['client-cert'] = dbus.ByteArray(
                "file://{0}\0".format(self.pfx_file).encode('utf8'))
            s_8021x_data['private-key'] = dbus.ByteArray(
                "file://{0}\0".format(self.pfx_file).encode('utf8'))
            s_8021x_data['private-key-password'] = self.user_data.password
            s_8021x_data['private-key-password-flags'] = 0
        s_con = dbus.Dictionary({
            'type': '802-11-wireless',
            'uuid': str(uuid.uuid4()),
            'permissions': ['user:' +
                            os.environ.get('USER')],
            'id': ssid
            })
        s_wifi = dbus.Dictionary({
            'ssid': dbus.ByteArray(ssid.encode('utf8')),
            'security': '802-11-wireless-security'
            })
        s_wsec = dbus.Dictionary({
            'key-mgmt': 'wpa-eap',
            'proto': ['rsn'],
            'pairwise': ['ccmp'],
            'group': ['ccmp', 'tkip']
            })
        s_8021x = dbus.Dictionary(s_8021x_data)
        s_ip4 = dbus.Dictionary({'method': 'auto'})
        s_ip6 = dbus.Dictionary({'method': 'auto'})
        con = dbus.Dictionary({
            'connection': s_con,
            '802-11-wireless': s_wifi,
            '802-11-wireless-security': s_wsec,
            '802-1x': s_8021x,
            'ipv4': s_ip4,
            'ipv6': s_ip6
            })
        self.settings.AddConnection(con)

    def add_connections(self, user_data):
        """Delete and then add connections to the system"""
        self.__check_opts()
        self.user_data = user_data
        for ssid in Config.ssids:
            self.__delete_existing_connection(ssid)
            self.__add_connection(ssid)
        for ssid in Config.del_ssids:
            self.__delete_existing_connection(ssid)


Messages.quit = "¿Deseas abandonar?"
Messages.username_prompt = "introduce tu identificador de usuario"
Messages.enter_password = "introduce la contraseña"
Messages.enter_import_password = "introduce tu contraseña de " \
    "importación"
Messages.incorrect_password = "contraseña incorrecta"
Messages.repeat_password = "repite tu contraseña"
Messages.passwords_difffer = "las contraseñas no coinciden"
Messages.installation_finished = "Instalación correcta"
Messages.cat_dir_exisits = "La carpeta {} ya existe. Algunos de sus " \
    "archivos pueden ser sobrescritos."
Messages.cont = "¿Continuar?"
Messages.nm_not_supported = "Esta versión de NetworkManager no está " \
    "soportada"
Messages.cert_error = "No se ha encontrado el archivo de certificado. " \
    "Parece un error de CAT."
Messages.unknown_version = "Versión desconocida"
Messages.dbus_error = "Problema con la conexión con DBus. Una " \
    "ejecución de sudo podría ayudar."
Messages.yes = "S"
Messages.no = "N"
Messages.p12_filter = "fichero con certificado personal (p12 o pfx)"
Messages.all_filter = "Todos los ficheros"
Messages.p12_title = "fichero con certificado personal (p12 o pfx)"
Messages.save_wpa_conf = "La configuración de NetworkManager falló, " \
    "pero podemos generar un archivo de configuración para wpa_supplicant " \
    "si lo deseas. Aviso: tu contraseña se almacenará sin cifrar en este " \
    "archivo."
Messages.save_wpa_confirm = "Escribir el archivo"
Messages.wrongUsernameFormat = "Error: tu nombre de usuario debe tener " \
    "la forma usuario@dominio. Por ejemplo: juan@example.net"
Messages.wrong_realm = "Error: tu nombre de usuario debe tener la " \
    "forma usuario@{}. Por favor, introduce el nombre de usuario de forma " \
    "correcta."
Messages.wrong_realm_suffix = "Error: tu nombre de usuario debe tener " \
    "la forma 'usuario@dominio' y terminar con '{}'. Por favor, introduce " \
    "el nombre de usuario de forma correcta."
Messages.user_cert_missing = "No se ha encontrado un certificado " \
    "personal"
Config.instname = "Universidad Católica del Norte"
Config.profilename = "Universidad Catolica del Norte - Sede Coquimbo"
Config.url = "eduroam.sede.ucn.cl"
Config.email = "dis@ucn.cl"
Config.title = "eduroam CAT"
Config.server_match = "eduroamcoq.ucn.cl"
Config.eap_outer = "TTLS"
Config.eap_inner = "PAP"
Config.init_info = "Este instalador ha sido preparado para {0}\n\nMás " \
    "información y comentarios:\n\nEMAIL: {1}\nWWW: {2}\n\nInstalador " \
    "creado con software del proyecto GEANT."
Config.init_confirmation = "Este instalador sólo funcionará " \
    "correctamente si eres miembro de {0}."
Config.user_realm = "ucn.cl"
Config.ssids = ['eduroam']
Config.del_ssids = []
Config.servers = ['DNS:eduroamcoq.ucn.cl']
Config.use_other_tls_id = False
Config.anonymous_identity = "roamer@ucn.cl"
Config.tou = ""
Config.CA = """-----BEGIN CERTIFICATE-----
MIIFBTCCA+2gAwIBAgIJAJ5Si7HDHs+lMA0GCSqGSIb3DQEBCwUAMIGfMQswCQYD
VQQGEwJDTDELMAkGA1UECAwCQ08xETAPBgNVBAcMCENvcXVpbWJvMScwJQYDVQQK
DB5Vbml2ZXJzaWRhZCBDYXRvbGljYSBkZWwgTm9ydGUxGzAZBgkqhkiG9w0BCQEW
DGFkbWluQHVjbi5jbDEqMCgGA1UEAwwhRW50aWRhZCBjZXJ0aWZpY2Fkb3JhIGVk
dXJvYW0gVUNOMB4XDTE4MDgxNDE0MDIzMFoXDTI4MDgxMTE0MDIzMFowgZ8xCzAJ
BgNVBAYTAkNMMQswCQYDVQQIDAJDTzERMA8GA1UEBwwIQ29xdWltYm8xJzAlBgNV
BAoMHlVuaXZlcnNpZGFkIENhdG9saWNhIGRlbCBOb3J0ZTEbMBkGCSqGSIb3DQEJ
ARYMYWRtaW5AdWNuLmNsMSowKAYDVQQDDCFFbnRpZGFkIGNlcnRpZmljYWRvcmEg
ZWR1cm9hbSBVQ04wggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDbTWVF
z8ETyMZG7BPn5dDOS1gHesjbSnF0jIoxBlO7VQVEZ2/ln6lxZUF5PVpsx0bPaBGx
CM1s9hnUQszcvmdFQ3kAoe59JWpMeWp5eaFQTjObK5WGwvlfKURLGuDzMALxvtcl
WMUdQ1LMvwXKTwiIir7Qwa7hgD7ngLzqZHTUnm5pLdVQcjMOlY1obSGpFYFMyc/J
N2CMP/kifzwHSpTr1OgjUaCQnxn0H8COnc0jBF09NqBPf91GbawXYuEF64kTj3IS
D2wlsqXbufc4+dh2Qq2LZZygweuKhkNV6xsjvRdbGhEXlNuozotrvQFmGuvBOC7a
nVMQ3+jxnmuppF+PAgMBAAGjggFAMIIBPDAdBgNVHQ4EFgQUy794ZcU6uRuREjJ1
jHEIHjQW6uQwgdQGA1UdIwSBzDCByYAUy794ZcU6uRuREjJ1jHEIHjQW6uShgaWk
gaIwgZ8xCzAJBgNVBAYTAkNMMQswCQYDVQQIDAJDTzERMA8GA1UEBwwIQ29xdWlt
Ym8xJzAlBgNVBAoMHlVuaXZlcnNpZGFkIENhdG9saWNhIGRlbCBOb3J0ZTEbMBkG
CSqGSIb3DQEJARYMYWRtaW5AdWNuLmNsMSowKAYDVQQDDCFFbnRpZGFkIGNlcnRp
ZmljYWRvcmEgZWR1cm9hbSBVQ06CCQCeUouxwx7PpTAMBgNVHRMEBTADAQH/MDYG
A1UdHwQvMC0wK6ApoCeGJWh0dHA6Ly93d3cuZXhhbXBsZS5jb20vZXhhbXBsZV9j
YS5jcmwwDQYJKoZIhvcNAQELBQADggEBAJrrFl4ymyfe5RRKQWZ3+hGRkPRv8EBD
ZeFp/1v42OhjCIAZaB/QNAU0LXKbaJqprVz2ZNCdIoLw+UoaWicVG7067whEjYLN
XshFu8mIrbgJMq7y7UNxdMMwqBq0ElgxXUa+2krsNqeRAX9f/5sSKSOVKUoi1ZUk
5hMJ8ptkSDLBi25TS5YGEzsEeNy4cAEBrdhAl2JVbOtEk17zsfbaABmaBnLJ9X2p
mED5pttPlRWsvl43QEwJowU1Hnjca2u5p+gH6vDZYJaWWBNajM69g/4EN3UocPPo
FClpgb1aueJ26EBp3FKC11jrsz1hXu0f9KNMdv3OeC/hNx77DRm78t0=
-----END CERTIFICATE-----
"""
run_installer()
