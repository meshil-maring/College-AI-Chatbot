"""Strict metadata checks reused before start, database access and cleanup."""
from .policy import (
    DATA_DIRECTORY, ENTRYPOINT, START_COMMAND, labels_for, name_for,
    require, validate_identity,
)


def validate_container(container, container_id, token, pins, *, running=None, image_labels=None):
    validate_identity(container_id, token)
    require(container.get("Id") == container_id, "Wrong container ID")
    require(container.get("Name") == "/" + name_for(token), "Wrong container name")
    require(container.get("Image") == pins.image_id, "Wrong container image ID")
    config = container.get("Config")
    host = container.get("HostConfig")
    state = container.get("State")
    network = container.get("NetworkSettings")
    require(all(isinstance(value, dict) for value in (config, host, state, network)),
            "Missing required container metadata")
    require({"Image", "Labels", "User", "Entrypoint", "Cmd", "Env", "Volumes"} <= set(config),
            "Missing required container configuration")
    require({"Ports", "Networks"} <= set(network), "Missing runtime network metadata")
    require(config.get("Image") == pins.image_id, "Wrong creation image identity")
    expected_labels = (image_labels or {}) | labels_for(token)
    require(config.get("Labels") == expected_labels, "Wrong container ownership labels")
    require(config.get("User") == pins.user, "Wrong database OS user")
    require(config.get("Entrypoint") == ENTRYPOINT
            and config.get("Cmd") == START_COMMAND, "Unreviewed startup command")
    require(isinstance(config.get("Env"), list), "Missing container environment metadata")
    pgdata = [value for value in config["Env"]
              if isinstance(value, str) and value.startswith("PGDATA=")]
    require(pgdata == [f"PGDATA={DATA_DIRECTORY}"], "Wrong PostgreSQL data directory")
    volumes = config.get("Volumes")
    require(volumes is None or (isinstance(volumes, dict)
            and set(volumes) <= {DATA_DIRECTORY}), "Unexpected declared volume")
    require(host.get("AutoRemove") is True, "Automatic removal is required")
    require(host.get("NetworkMode") == "none", "Network exposure prohibited")
    require(host.get("PublishAllPorts") is False, "Published ports prohibited")
    require(host.get("PortBindings") == {}, "Host port bindings prohibited")
    ports = network["Ports"]
    require(ports is None or (isinstance(ports, dict)
            and all(value in (None, []) for value in ports.values())),
            "Runtime port exposure prohibited")
    networks = network.get("Networks")
    require(isinstance(networks, dict) and set(networks) <= {"none"},
            "Unexpected attached network")
    if state.get("Running") is True:
        require(set(networks) == {"none"}, "Missing isolated runtime network")
    for key in ("Binds", "Mounts", "VolumesFrom", "Devices", "DeviceRequests",
                "DeviceCgroupRules", "CapAdd"):
        require(key in host and host[key] in (None, []),
                "Unexpected storage, device or capability exposure")
    require(host.get("Tmpfs") == {DATA_DIRECTORY: pins.tmpfs}, "Wrong bounded data tmpfs")
    mounts = container.get("Mounts")
    require(isinstance(mounts, list) and len(mounts) <= 1, "Unexpected container mounts")
    if mounts:
        mount = mounts[0]
        require(isinstance(mount, dict) and mount.get("Type") == "tmpfs"
                and mount.get("Destination") == DATA_DIRECTORY
                and mount.get("Source") in (None, "")
                and mount.get("RW") is True, "Persistent or unexpected mount")
    require(host.get("Privileged") is False and host.get("ReadonlyRootfs") is True,
            "Unsafe container privileges or writable root filesystem")
    require(host.get("CapDrop") == ["ALL"], "All capabilities must be dropped")
    require(host.get("SecurityOpt") == ["no-new-privileges:true"],
            "Unexpected security options")
    for key, expected in (("PidMode", ""), ("IpcMode", "private"), ("UTSMode", ""),
                          ("CgroupnsMode", "private"), ("UsernsMode", "")):
        require(host.get(key) == expected, "Namespace sharing prohibited")
    require(type(state.get("Running")) is bool, "Missing container state")
    require(state.get("Paused") is False and state.get("Restarting") is False,
            "Paused or restarting container prohibited")
    require(state.get("Status") in {"created", "running", "exited"},
            "Unexpected container lifecycle state")
    require(state["Running"] == (state["Status"] == "running"),
            "Contradictory container lifecycle state")
    if running is not None:
        require(state["Running"] is running, "Unexpected running state")
        if running is False:
            require(state["Status"] == "created", "Startup requires a fresh created container")
    return container
