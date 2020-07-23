Appliance
=========

This document describes how to create a VMware compatible appliance that runs Open
Zaak.

Setting up your environment
---------------------------

The following (free) software is required to create the appliance.

* `Python`_ 3.5 (or higher)
* `Debian installation image`_ 10.0 (or higher)
* `Oracle VirtualBox`_ 5.2 (or higher)
* `VMware OVF-tool`_ 4.0 (or higher)
* `Node.js`_ 10.0 (or higher)

Optionally, you can install `VMware Workstation Player`_ (15.5 or higher) which is
only free for non-commercial use. In this document, we only use it to test our
appliance after conversion with the `VMware OVF-tool`_.

Before you get started
----------------------

1. Make sure the `VMware OVF-tool`_ and `Oracle VirtualBox`_ executables are
   available via your ``PATH``. You can check this with::

        $ vboxmanage --version
        5.2.2r119230

        $ ovftool --version
        VMware ovftool 4.3.0 (build-14746126)

2. Download the latest `Debian installation image`_. For example:
   ``debian-10.2.0-amd64-netinst.iso``.

3. Modify ``debian-config/preseed.cfg`` to match your needs for the
   installation. Take special note to following sections:

   * Account setup: Root- and User-account passwords are now "insecure"

4. Figure out your bridge adapter that has an internet connection::

        $ vboxmanage list bridgedifs | grep "Name:  \|Status"
        Name:            Realtek PCIe GBE Family Controller
        Status:          Up
        Name:            VirtualBox Host-Only Ethernet Adapter
        Status:          Down
        Name:            Realtek RTL8723BE Wireless LAN 802.11n PCI-E NIC
        Status:          Down

   Typically, you see one entry with the status "Up" that you can use. In the above
   case, the network adapter name is "Realtek PCIe GBE Family Controller"

Create the base container
-------------------------

1. Allow the Debian installer to download our configuration details from the host
   system. In a separate terminal, in the root folder of the project, do::

        $ npm install

        $ npm run appliance:serve-config
        Starting up http-server, serving [...]/debian-config
        Available on:
          http://192.168.X.X:8080
          http://127.0.0.1:8080

2. Create the container and follow the instructions. Run ``create-container.sh`` and
   pass the ISO-file and the network adapter name that has an internet connection::

        $ ./create-container.sh debian-10.2.0-amd64-netinst.iso "Realtek PCIe GBE Family Controller"
        [...]
        Continue with the OS installation procedure in container. Press return when done...

3. In the VirtualBox console, after the initial boot procedure:

   a. Choose ``Advanced options`` > ``Automated install``
   b. When asked for an initial preconfiguration file, fill in the URL from
      the ``npm run appliance:serve-config`` script, followed by the path
      ``/preseed.cfg``. For example::

            http://192.168.X.X:8080/preseed.cfg

   c. After you see a log entry in the terminal running the
      ``npm run appliance:serve-config`` script, you can close it.
   d. When the installation is done, the VirtualBox container shuts down automatically.

4. In your terminal, press return to continue::

        Creating snapshot (initial-install)...
        [...]
        Continue with the installation procedure in container and shut down when completed. Press return when done...

   A snapshot called "initial-install" is created to easily reset the image. The
   VirtualBox container will start again to allow for the installation of Open Zaak.

5. The VirtualBox console will show something like::

        Debian GNU/Linux 10 debian tty1

        My IP-address: 192.168.X.X
        debian login:

You can now continue to install Open Zaak.

Install Open Zaak
-----------------

1. Navigate to the Open Zaak deployment folder for a single server setup::

        $ cd deployment/single-server

2. Add the IP-address from the container to the ``hosts`` file or create a new
   ``hosts`` file to have an entry like this::

        192.168.X.X ansible_python_interpreter=/usr/bin/python3

   Instead of an IP-address, it's recommended to **use a domain name**. Without a
   domain name it's more complicated to get everything to work and HTTPS is disabled.
   If you use a domain name, you can use that instead of the IP-address that is used
   in throughout the rest of this document.

3. Configure the relevant variables. Make a copy of the example file and adjust it
   to fit your preferences::

        $ cp vars/open-zaak.example.yml vars/open-zaak.yml

4. Assuming you did not change the user account in ``preseed.cfg``, start the
   installation:

   a. Login to the container to verify and accept its connection::

        $ ssh openzaak@192.168.X.X
        [...]
        Are you sure you want to continue connecting (yes/no)? yes
        openzaak@debian:~$ logout

   b. Install Ansible requirements::

        $ ansible-galaxy collection install -r requirements.yml
        $ ansible-galaxy role install -r requirements.yml

   c. Deploy Open Zaak and limit the installation to the container. If you use
      a domain name and want to make use of HTTPS (recommended), you can leave out
      ``--extra-vars "openzaak_ssl=false""``::

        $ ansible-playbook open-zaak.yml \
          --user=openzaak \
          --become \
          --ask-become-pass \
          --ask-pass \
          --limit=192.168.X.X \
          --extra-vars "openzaak_ssl=false"

        SSH password: <the password of the "openzaak" user as given in preseed.cfg>
        BECOME password[defaults to SSH password]: <same as above>

4. After the installation, you might want to create a superuser already. In the
   console or SSH-session, do::

        openzaak@debian:~$ sudo docker exec -it openzaak-0 /app/src/manage.py createsuperuser

5. When done, you can shutdown the container from the console or SSH-session::

        openzaak@debian:~$ sudo /sbin/shutdown now

6. Back to the terminal, you now press enter to continue::

        Creating snapshot (component-install)...
        [...]
        Done.

   A snapshot called "component-install" is created to easily reset the image.

You can now continue to convert the container to be compatible VMware.

Convert to VMware
-----------------

1. Convert the VirtualBox container to a VMware-compatible container, using the
   ``export-ovf.sh`` script::

        $ ./export-ovf.sh
        Exporting to OVF...
        0%...10%...20%...30%...40%...50%...60%...70%...80%...90%...100%
        Successfully exported 1 machine(s).
        Exporting to VMX...
        Opening OVF source: openzaak.ovf
        Opening VMX target: openzaak.vmx
        Writing VMX file: openzaak.vmx
        Transfer Completed
        Warning:
         - No manifest file found.
         - Wrong file size specified in OVF descriptor for 'openzaak-disk001.vmdk' (specified: -1, actual 2359223808).
         - No manifest entry found for: 'openzaak-disk001.vmdk'.
        Completed successfully
        Done.

You can now continue to test the appliance.

Test the appliance
------------------

1. Start `VMware Workstation Player`_ and open ``openzaak.vmx``.

2. Power on the container.

3. Make sure the console indicates a valid IP-address.

4. You can now open your browser and navigate to the above IP-address or domain name
   you configured using either ``http`` or ``https``, depending on your choices.

Common issues
~~~~~~~~~~~~~

* **No IP-address is shown after installing the VirtualBox container**

  Make sure the virtual machine is linked to a network adapter that works. Also, you
  need a DHCP-server active in the network to provide your virtual machine with an IP
  or modify the network configuration in the console to obtain a static IP-address.

* **No internet connection in VMware Workstatation Player**
  Converting from VirtualBox to VMware might influence your network interfaces.
  Login to the console and change the primary network interface::

        $ ip addr
        [...]
        $ nano /etc/network/interfaces

  Typically, replace ``enp0s3`` with ``ens32`` so it reads::

        # Primary networking interfaces
        auto ens32
        iface ens32 inet dhcp

  Restart the network services::

        $ /etc/init.d/networking restart

* **The web interface just shows "Bad Request"**

  Most likely, you installed Open Zaak using a different domain name or
  IP-address compared to the one you are using to access the website now.

  You need to either use the same domain name or IP-address, or change the
  Nginx and Django settings to accept the new domain or IP-address.

  Change ``ALLOWED_HOSTS`` in::

        $ nano /home/openzaak/.env

  Change ``server_name`` in::

        $ nano /etc/nginx/conf.d/openzaak.conf


.. _`Python`: https://www.python.org/downloads/
.. _`Debian installation image`: https://www.debian.org/distrib/
.. _`Oracle VirtualBox`: https://www.virtualbox.org/wiki/Downloads
.. _`VMware OVF-tool`: https://code.vmware.com/web/tool/ovf
.. _`Node.js`: https://nodejs.org/en/download/
.. _`VMware Workstation Player`: https://www.vmware.com/products/workstation-player.html

