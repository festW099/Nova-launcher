import minecraft_launcher_lib as mcl
from typing import List, Dict, Optional

class MinecraftManager:
    def __init__(self, minecraft_directory: str):
        self.minecraft_directory = minecraft_directory

    def get_version_list(self) -> List[Dict]:
        versions = []
        # Основные версии
        for v in mcl.utils.get_version_list():
            versions.append({
                'id': v['id'],
                'type': v.get('type', 'release'),
                'display': f"{v['id']} ({v.get('type', 'release')})"
            })

        # Forge
        try:
            for version in mcl.forge.list_forge_versions():
                versions.append({
                    'id': version,
                    'type': 'forge',
                    'display': f"{version} (forge)"
                })
        except Exception as e:
            print(f"Failed to load Forge versions: {e}")

        # Fabric
        try:
            fabric_versions = mcl.fabric.get_all_minecraft_versions()
            for v in fabric_versions:
                if v['stable']:
                    versions.append({
                        'id': v['version'],
                        'type': 'fabric',
                        'display': f"{v['version']} (fabric)"
                    })
        except Exception as e:
            print(f"Failed to load Fabric versions: {e}")

        return versions

    def install_version(self, version_id: str, version_type: str, callback: dict):
        if version_type == "forge":
            mcl.forge.install_forge_version(version_id, self.minecraft_directory, callback=callback)
        elif version_type == "fabric":
            mcl.fabric.install_fabric(version_id, self.minecraft_directory, callback=callback)
        else:
            mcl.install.install_minecraft_version(version_id, self.minecraft_directory, callback=callback)

    def get_launch_command(self, version_id: str, version_type: str, options: dict) -> list:
        if version_type == "fabric":
            loader = mcl.fabric.get_latest_loader_version()
            version_name = f"fabric-loader-{loader}-{version_id}"
            return mcl.command.get_minecraft_command(version_name, self.minecraft_directory, options)
        elif version_type == "forge":
            return mcl.command.get_minecraft_command(version_id, self.minecraft_directory, options)
        else:
            return mcl.command.get_minecraft_command(version_id, self.minecraft_directory, options)