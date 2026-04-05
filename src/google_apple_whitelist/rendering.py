from __future__ import annotations

import json
import os
import pathlib
import re
import tempfile
from dataclasses import dataclass

_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_]+")


@dataclass(frozen=True)
class RenderSummary:
    input_dir: pathlib.Path
    output_dir: pathlib.Path
    dataset: str
    rendered_files: tuple[str, ...]


def _write_text_atomic(path: pathlib.Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path_str = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = pathlib.Path(tmp_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _read_cidrs(path: pathlib.Path) -> tuple[str, ...]:
    if not path.exists():
        return ()
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            lines.append(stripped)
    return tuple(lines)


def _sanitize_set_prefix(value: str) -> str:
    value = _SAFE_NAME_RE.sub("_", value.strip())
    value = value.strip("_")
    if not value:
        return "gaw"
    return value[:20]


def build_nginx_allow_conf(cidrs: tuple[str, ...]) -> str:
    lines = [f"allow {cidr};" for cidr in cidrs]
    lines.append("deny all;")
    return "\n".join(lines) + "\n"


def build_nginx_real_ip_conf(cidrs: tuple[str, ...]) -> str:
    lines = [f"set_real_ip_from {cidr};" for cidr in cidrs]
    lines.extend(
        [
            "real_ip_header CF-Connecting-IP;",
            "real_ip_recursive on;",
        ]
    )
    return "\n".join(lines) + "\n"


def build_ipset_restore(
    set_prefix: str,
    ipv4_cidrs: tuple[str, ...],
    ipv6_cidrs: tuple[str, ...],
) -> str:
    v4_set = f"{set_prefix}_allow_v4"
    v6_set = f"{set_prefix}_allow_v6"
    lines = [
        f"create {v4_set} hash:net family inet -exist",
        f"create {v6_set} hash:net family inet6 -exist",
        f"flush {v4_set}",
        f"flush {v6_set}",
    ]
    lines.extend(f"add {v4_set} {cidr}" for cidr in ipv4_cidrs)
    lines.extend(f"add {v6_set} {cidr}" for cidr in ipv6_cidrs)
    return "\n".join(lines) + "\n"


def build_nftables_snippet(
    set_prefix: str,
    ipv4_cidrs: tuple[str, ...],
    ipv6_cidrs: tuple[str, ...],
) -> str:
    v4_set = f"{set_prefix}_allow_v4"
    v6_set = f"{set_prefix}_allow_v6"

    def _render_elements(cidrs: tuple[str, ...], indent: str = "      ") -> str:
        if not cidrs:
            return ""
        return ",\n".join(f"{indent}{cidr}" for cidr in cidrs)

    v4_elements = _render_elements(ipv4_cidrs)
    v6_elements = _render_elements(ipv6_cidrs)
    return (
        f"set {v4_set} {{\n"
        f"    type ipv4_addr\n"
        f"    flags interval\n"
        f"    elements = {{\n"
        f"{v4_elements}\n"
        f"    }}\n"
        f"}}\n\n"
        f"set {v6_set} {{\n"
        f"    type ipv6_addr\n"
        f"    flags interval\n"
        f"    elements = {{\n"
        f"{v6_elements}\n"
        f"    }}\n"
        f"}}\n"
    )


def render_artifacts(
    input_dir: pathlib.Path,
    output_dir: pathlib.Path,
    dataset: str = "combined_google_services_plus_apple",
    set_prefix: str = "gaw",
) -> RenderSummary:
    dataset_ipv4 = _read_cidrs(input_dir / f"{dataset}_ipv4.txt")
    dataset_ipv6 = _read_cidrs(input_dir / f"{dataset}_ipv6.txt")
    if not dataset_ipv4 and not dataset_ipv6:
        raise FileNotFoundError(
            f"Could not find {dataset}_ipv4.txt or {dataset}_ipv6.txt in {input_dir}"
        )

    cloudflare_ipv4 = _read_cidrs(input_dir / "cloudflare_proxy_ipv4.txt")
    cloudflare_ipv6 = _read_cidrs(input_dir / "cloudflare_proxy_ipv6.txt")
    set_prefix = _sanitize_set_prefix(set_prefix)

    rendered_files: list[str] = []

    def _emit(relative_path: str, content: str) -> None:
        _write_text_atomic(output_dir / relative_path, content)
        rendered_files.append(relative_path)

    _emit(f"nginx/{dataset}_allow.conf", build_nginx_allow_conf(dataset_ipv4 + dataset_ipv6))
    _emit(f"ipset/{dataset}.restore", build_ipset_restore(set_prefix, dataset_ipv4, dataset_ipv6))
    _emit(f"nftables/{dataset}.nft", build_nftables_snippet(set_prefix, dataset_ipv4, dataset_ipv6))

    if cloudflare_ipv4 or cloudflare_ipv6:
        _emit("nginx/cloudflare_real_ip.conf", build_nginx_real_ip_conf(cloudflare_ipv4 + cloudflare_ipv6))
        _emit("nginx/cloudflare_origin_allow.conf", build_nginx_allow_conf(cloudflare_ipv4 + cloudflare_ipv6))

    metadata = {
        "dataset": dataset,
        "set_prefix": set_prefix,
        "counts": {
            "dataset_ipv4": len(dataset_ipv4),
            "dataset_ipv6": len(dataset_ipv6),
            "cloudflare_ipv4": len(cloudflare_ipv4),
            "cloudflare_ipv6": len(cloudflare_ipv6),
        },
        "rendered_files": rendered_files,
    }
    _emit("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    return RenderSummary(
        input_dir=input_dir,
        output_dir=output_dir,
        dataset=dataset,
        rendered_files=tuple(rendered_files),
    )
