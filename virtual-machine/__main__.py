import pulumi
import pulumi_proxmoxve as proxmoxve
import os
import yaml

pulumi_config = pulumi.Config("talos-vm")

provider = proxmoxve.Provider(
    "proxmoxve",
    endpoint=pulumi_config.require("proxmox_endpoint"),
    insecure=False,
    api_token=pulumi_config.require("proxmox_api_token"),
    username=pulumi_config.require("proxmox_username"),
    password=pulumi_config.require("proxmox_password"),
)

config_path = "./config/"


def load_yaml_config(config_path):
    config_data = []
    try:
        config_files = [
            file for file in os.listdir(config_path) if file.endswith(".yaml")
        ]
        for file in config_files:
            with open(os.path.join(config_path, file), "r") as f:
                yaml_data = yaml.safe_load(f)
                config_data.append(yaml_data)
    except Exception as e:
        print(f"Error loading YAML files: {e}")
    return config_data


config_values = load_yaml_config(config_path)

vms = []

for config in config_values:
    file_download = config.get("file_download", {})
    resource_options = config.get("resource_options", {})
    virtual_machine = config.get("virtual_machine", {})

    talos_iso = proxmoxve.download.File(
        resource_name=file_download.get("resource_name", ""),
        overwrite=file_download.get("overwrite"),
        overwrite_unmanaged=file_download.get("overwrite_unmanaged"),
        content_type=file_download.get("content_type"),
        datastore_id=file_download.get("datastore_id"),
        file_name=file_download.get("file_name"),
        node_name=file_download.get("node_name"),
        url=file_download.get("url"),
        opts=pulumi.ResourceOptions(
            provider=provider,
            retain_on_delete=resource_options.get("retain_on_delete"),
        ),
    )

    for vm in range(virtual_machine.get("count", 1)):
        disks = []
        for disk_dict in virtual_machine.get("disks", []):
            for disk_name, disk_values in disk_dict.items():
                disks.append(
                    proxmoxve.vm.VirtualMachineDiskArgs(
                        interface=disk_values.get("interface"),
                        datastore_id=disk_values.get("datastore_id"),
                        file_format=disk_values.get("file_format"),
                        size=disk_values.get("size"),
                        iothread=disk_values.get("iothread"),
                        ssd=disk_values.get("ssd"),
                        discard=disk_values.get("discard"),
                        speed=disk_values.get("speed"),
                    )
                )

        network_devices = []
        for net_device_dict in virtual_machine.get("network_devices", []):
            for net_name, net_values in net_device_dict.items():
                network_devices.append(
                    proxmoxve.vm.VirtualMachineNetworkDeviceArgs(
                        bridge=net_values.get("bridge"),
                        model=net_values.get("model"),
                        vlan_id=net_values.get("vlan_id"),
                    )
                )

        vm = proxmoxve.vm.VirtualMachine(
            acpi=virtual_machine.get("acpi"),
            resource_name=virtual_machine.get("resource_name") + f"-{vm + 1}",
            name=virtual_machine.get("name") + f"-0{vm + 1}",
            description=virtual_machine.get("description"),
            tags=virtual_machine.get("tags", []),
            node_name=virtual_machine.get("node_name"),
            vm_id=virtual_machine.get("vm_id") + vm,
            bios=virtual_machine.get("bios"),
            machine=virtual_machine.get("machine_type"),
            boot_orders=virtual_machine.get("boot_orders"),
            on_boot=virtual_machine.get("on_boot"),
            started=virtual_machine.get("started"),
            reboot=virtual_machine.get("reboot"),
            stop_on_destroy=virtual_machine.get("stop_on_destroy"),
            keyboard_layout=virtual_machine.get("keyboard_layout"),
            timeout_clone=virtual_machine.get("timeout_clone"),
            timeout_create=virtual_machine.get("timeout_create"),
            timeout_migrate=virtual_machine.get("timeout_migrate"),
            timeout_reboot=virtual_machine.get("timeout_reboot"),
            timeout_shutdown_vm=virtual_machine.get("timeout_shutdown"),
            timeout_start_vm=virtual_machine.get("timeout_start"),
            timeout_stop_vm=virtual_machine.get("timeout_stop"),
            scsi_hardware=virtual_machine.get("scsi_hardware"),
            vga=proxmoxve.vm.VirtualMachineVgaArgs(
                type=virtual_machine["vga"].get("type"),
            ),
            agent=proxmoxve.vm.VirtualMachineAgentArgs(
                enabled=virtual_machine["agent"].get("enabled"),
                trim=virtual_machine["agent"].get("trim"),
            ),
            memory=proxmoxve.vm.VirtualMachineMemoryArgs(
                dedicated=virtual_machine["memory"].get("dedicated"),
            ),
            cpu=proxmoxve.vm.VirtualMachineCpuArgs(
                architecture=virtual_machine["cpu"].get("architecture"),
                type=virtual_machine["cpu"].get("type"),
                sockets=virtual_machine["cpu"].get("sockets"),
                cores=virtual_machine["cpu"].get("cores"),
            ),
            disks=disks,
            efi_disk=proxmoxve.vm.VirtualMachineEfiDiskArgs(
                datastore_id=virtual_machine["efi_disk"].get("datastore_id"),
                file_format=virtual_machine["efi_disk"].get("file_format"),
                pre_enrolled_keys=virtual_machine["efi_disk"].get("pre_enrolled_keys"),
                type=virtual_machine["efi_disk"].get("type"),
            ),
            cdrom=proxmoxve.vm.VirtualMachineCdromArgs(
                enabled=virtual_machine["cdrom"].get("enabled"),
                interface=virtual_machine["cdrom"].get("interface"),
                file_id=talos_iso.id,
            ),
            network_devices=network_devices,
            operating_system=proxmoxve.vm.VirtualMachineOperatingSystemArgs(
                type=virtual_machine["operating_system"].get("type"),
            ),
            serial_devices=[],
            opts=pulumi.ResourceOptions(
                provider=provider,
                ignore_changes=resource_options.get("ignore_changes"),
            ),
        )
        vms.append(vm)

for vm in vms:
    pulumi.export(f"vm{(vms.index(vm))+1}_name", vm.name)
    pulumi.export(f"vm{(vms.index(vm))+1}_id", vm.id)
    pulumi.export(f"vm{(vms.index(vm))+1}_ip1", vm.ipv4_addresses[1:][6][0])
    pulumi.export(f"vm{(vms.index(vm))+1}_ip2", vm.ipv4_addresses[1:][7][0])
    pulumi.export(f"vm{(vms.index(vm))+1}_mac1", vm.network_devices[0]["mac_address"])
    pulumi.export(f"vm{(vms.index(vm))+1}_mac2", vm.network_devices[1]["mac_address"])
