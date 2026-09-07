c = get_config()  # noqa

c.ServerProxy.servers = {
    "zensical": {
        "command": [
            "bash",
            ".binder/start-zensical.sh",
            "{port}",
            "{base_url}zensical/",
        ],
        "timeout": 30,
        "launcher_entry": {
            "title": "Zensical Preview",
            "category": "Documentation",
        },
        "new_browser_tab": True,
    }
}
