Appliance
=========

Setting up your environment
---------------------------

The following (free) software is required to create the appliance.

* `Python`_ 3.5 (or higher)
* `Debian installation image`_ 10.0 (or higher)
* `Oracle VirtualBox`_ 5.2 (or higher)
* `VMware OVF-tool`_ 4.0 (or higher)
* `Node.js`_ 10.0 (or higher)
* `VMware Workstation Player`_ (15.5 or higher, optional)

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

4. In the ``create-container.sh`` script, change the ``BRIDGE_ADAPTER`` to match
   your network adapter name that is connected to the internet. You can find
   this in your VirtualBox interface.

Create the base container
-------------------------

1. Allow the Debian installer to download our configuration details from the
   host system. In a seperate terminal, do::

        $ npm install http-server

        $ ./serve-debian-config.sh
        Starting up http-server, serving [...]/debian-config
        Available on:
          http://192.168.X.X:8080
          http://127.0.0.1:8080

2. Create the container and follow the instructions::

        $ ./create-container.sh debian-10.2.0-amd64-netinst.iso
        [...]
        Start OS installation in VirtualBox container...
        (continue with the OS installation procedure in container)

3. In the VirtualBox console:

   a. Choose ``Advanced options`` > ``Automated install``
   b. When asked for an initial preconfiguration file, fill in the URL from
      the ``serve-debian-config.sh`` script, followed by the path
      ``/preseed.cfg``. For example::

            http://192.168.X.X:8080/preseed.cfg

   c. When the installation is done, the container shuts down automatically.

4. In your terminal, press a key to continue::

        VirtualBox container was closed. Press any key to continue...
        [...]
        Launching VirtualBox container...
        (continue with the Open Zaak installation procedure in container and shut down when done)

   A snapshot called "initial-install" is created to easily reset the image.

5. Log in to the container console as ``root`` to figure out its IP-address::

        root@debian:~# ip addr

6. Finally, you can show the IP-address when the container boots::

        root@debian:~# echo 'My IP-address: \4' >> /etc/issue

Install Open Zaak
-----------------

1. Navigate to the Open Zaak deployment folder for a single server setup::

        $ cd deployment/single-server

2. Add the IP-address from the container to the ``hosts`` file::

        192.168.X.X ansible_python_interpreter=/usr/bin/python3

* TODO: Replace IP with domain!
* TODO: Removed ``role: geerlingguy.certbot`` from ``open-zaak.yml``
* TODO: Removed the entire SSL/HTTPS section from ``templates/openzaak.conf.j2``

3. Assuming you did not change the user account in ``preseed.cfg``, start the
   installation:

   a. Login to the container and logout again to verify and accept its
      connection::

        $ ssh openzaak@192.168.X.X
        [...]
        Are you sure you want to continue connecting (yes/no)? yes
        openzaak@debian:~$ logout

   b. Deploy Open Zaak and limit the installation to the container::

        $ ansible-playbook --user=openzaak --become --ask-pass --ask-vault-pass --limit=192.168.X.X open-zaak.yml
        SSH password: <the password of the "openzaak" user as given in preseed.cfg>
        Vault password: <the ansible vault password>

4. When done, you can shutdown the container from the console::

        openzaak@debian:~$ sudo /sbin/shutdown now

   A snapshot called "openzaak-install" is created to easily reset the image.

Convert to VMware
-----------------

1. Convert the VirtualBox container to a VMware-compatible container::

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

Test the appliance
------------------

1. Start `VMware Workstation Player`_ and open ``openzaak.vmx``.

2. Power on the container.

Common issues
~~~~~~~~~~~~~

* **No internet connection**

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

* **The website shows Bad Request**

  Most likely, you installed Open Zaak using a different domain name or
  IP-address compared to the one you are using to access the website now.

  You need to either use the same domain name or IP-address, or change the
  Nginx and Django settings to accept the new domain or IP-address.


.. _`Python`: https://www.python.org/downloads/
.. _`Debian installation image`: https://www.debian.org/distrib/
.. _`Oracle VirtualBox`: https://www.virtualbox.org/wiki/Downloads
.. _`VMware OVF-tool`: https://code.vmware.com/web/tool/ovf
.. _`Node.js`: https://nodejs.org/en/download/
.. _`VMware Workstation Player`: https://www.vmware.com/products/workstation-player.html

