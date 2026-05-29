from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

LIB_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = LIB_DIR.parent
REF_DIR = SCRIPTS_DIR.parent
PROTO_ROOT = REF_DIR / "proto"
PROTO_SPARK_DIR = PROTO_ROOT / "spark"
GENERATED_ROOT = SCRIPTS_DIR / "_generated"

PROTO_FILES = [
    PROTO_SPARK_DIR / "spark.proto",
    PROTO_SPARK_DIR / "spark_sampler.proto",
    PROTO_SPARK_DIR / "spark_heap.proto",
    PROTO_SPARK_DIR / "spark_ws.proto",
]


def ensure_generated_proto(protoc_bin: Optional[str] = None) -> None:
    expected = GENERATED_ROOT / "spark" / "spark_sampler_pb2.py"

    if not all(p.exists() for p in PROTO_FILES):
        missing = [str(p) for p in PROTO_FILES if not p.exists()]
        raise FileNotFoundError(f"Missing proto files: {missing}")

    need_compile = not expected.exists()
    if not need_compile:
        out_mtime = expected.stat().st_mtime
        need_compile = any(p.stat().st_mtime > out_mtime for p in PROTO_FILES)

    if need_compile:
        GENERATED_ROOT.mkdir(parents=True, exist_ok=True)
        resolved = protoc_bin or os.environ.get("PROTOC") or shutil.which("protoc") or shutil.which("protoc.exe")
        if resolved:
            cmd = [
                resolved,
                f"--proto_path={PROTO_ROOT}",
                f"--python_out={GENERATED_ROOT}",
                "spark/spark.proto",
                "spark/spark_sampler.proto",
                "spark/spark_heap.proto",
                "spark/spark_ws.proto",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                raise RuntimeError(
                    "protoc failed.\n"
                    f"stdout:\n{proc.stdout}\n"
                    f"stderr:\n{proc.stderr}"
                )
        else:
            cmd = [
                sys.executable,
                "-m",
                "grpc_tools.protoc",
                f"-I{PROTO_ROOT}",
                f"--python_out={GENERATED_ROOT}",
                "spark/spark.proto",
                "spark/spark_sampler.proto",
                "spark/spark_heap.proto",
                "spark/spark_ws.proto",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                raise RuntimeError(
                    "No protoc in PATH and grpc_tools.protoc unavailable. "
                    "Install protobuf compiler or run: pip install grpcio-tools\n"
                    f"stdout:\n{proc.stdout}\n"
                    f"stderr:\n{proc.stderr}"
                )
        pkg = GENERATED_ROOT / "spark"
        pkg.mkdir(parents=True, exist_ok=True)
        init_file = pkg / "__init__.py"
        if not init_file.exists():
            init_file.write_text("", encoding="utf-8")

    if str(GENERATED_ROOT) not in sys.path:
        sys.path.insert(0, str(GENERATED_ROOT))