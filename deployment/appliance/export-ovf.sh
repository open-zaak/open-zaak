#!/bin/bash
VM_NAME=openzaak

# Check if a VirtualBox container exists.
if [ ! -f ${VM_NAME}/${VM_NAME}.vdi ]; then
    echo -n >&2 "Error: VirtualBox container \"${VM_NAME}/${VM_NAME}.vdi\" not found."
    exit 1
fi

# Check if VBoxManage is available.
command -v vboxmanage >/dev/null 2>&1 || { echo >&2 "Error: The executable \"vboxmanage\" could not be found."; exit 1; }

# Check if OVF-tool is available.
command -v ovftool >/dev/null 2>&1 || { echo >&2 "Error: The executable \"ovftool\" could not be found."; exit 1; }

cd ${VM_NAME}

# vboxmanage snapshot ${VM_NAME} take "component-install"
rm -rf ${VM_NAME}.ovf
rm -rf ${VM_NAME}-disk001.vmdk

echo "Exporting to OVF..."

vboxmanage export ${VM_NAME} --output ${VM_NAME}.ovf --vsys 0 --product="Open Zaak" --producturl="https://gith
ub.com/open-zaak/open-zaak" --vendor="Maykin Media" --vendorurl="https://www.maykinmedia.nl" --version="1.0.0-alpha" --description="Open Zaak is een moderne, open source gegevens- en services-laag om zaakgericht werken te ondersteunen."

# Change virtualbox-2.2 to vmx-07 (the version matters for compatibility with VMWare).
# Error message: Unsupported hardware family 'virtualbox-2.2'.
# See: http://www.baconapplications.com/export-a-virtualbox-machine-to-vmware/
sed -i 's/virtualbox-2\.2/vmx-07/g' ${VM_NAME}.ovf
# Change Debian 64-Bit to Linux 64-Bit because the first is unrecognized.
# Warning message: [...] 'Debian10_64' (id: 96) is not supported [...] It will be mapped to [...]: 'Other (32-bit)'.
# See: https://users.suse.com/~kkaempf/cim/class/CIM_OperatingSystem.html
sed -i 's/<OperatingSystemSection ovf:id="96">/<OperatingSystemSection ovf:id="101">/g' ${VM_NAME}.ovf

echo "Exporting to VMX..."

ovftool ${VM_NAME}.ovf ${VM_NAME}.vmx

echo "Done."
