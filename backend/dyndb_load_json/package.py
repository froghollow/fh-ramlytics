#!/usr/bin/env python3
"""
Cross-platform Lambda deployment package creator using uv.
Works on Windows, Mac, and Linux.

Builds two artifacts:
  - lambda_layer.zip:    this member's third-party + workspace dependencies, for a Lambda Layer.
  - lambda_function.zip: just the handler code, meant to be deployed alongside the layer.
"""

import os
import shutil
import subprocess
import zipfile
from pathlib import Path

# Provided by the Lambda Python runtime already; no need to bundle these.
RUNTIME_PROVIDED_PACKAGES = ['boto3', 'botocore', 's3transfer', 'jmespath']


def _zip_dir(source_dir: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for file in files:
                if file.endswith('.pyc') or file == '.lock':
                    continue
                file_path = Path(root) / file
                arcname = file_path.relative_to(source_dir)
                zipf.write(file_path, arcname)


def create_layer_package(project_name, build_dir, workspace_root):
    """Build a Lambda Layer zip containing this member's dependencies."""

    layer_dir = build_dir / 'layer'
    # Lambda layers must place packages under a python/ (or python/lib/pythonX.Y/site-packages/) prefix.
    layer_site_packages = layer_dir / 'python'
    layer_zip_path = build_dir.parent / 'lambda_layer.zip'
    requirements_path = build_dir / 'requirements.txt'

    layer_site_packages.mkdir(parents=True, exist_ok=True)

    print(f"Resolving dependencies for '{project_name}'...")
    export_cmd = [
        'uv', 'export', '--project', str(workspace_root),
        '--package', project_name,
        '--no-dev', '--no-editable', '--no-hashes',
        '-o', str(requirements_path),
    ]
    for pkg in RUNTIME_PROVIDED_PACKAGES:
        export_cmd += ['--no-emit-package', pkg]
    subprocess.run(export_cmd, check=True)

    print(f"Installing dependencies into {layer_site_packages}...")
    subprocess.run(
        ['uv', 'pip', 'install', '--target', str(layer_site_packages), '-r', str(requirements_path), '--no-deps'],
        cwd=workspace_root,
        check=True,
    )

    # Remove dist-info/pycache noise from the installed packages
    for item in layer_site_packages.iterdir():
        if item.name.endswith('.dist-info') or item.name == '__pycache__':
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

    print("Creating layer package...")
    _zip_dir(layer_dir, layer_zip_path)

    size_mb = layer_zip_path.stat().st_size / (1024 * 1024)
    print(f"✅ Layer package created: {layer_zip_path}")
    print(f"   Size: {size_mb:.2f} MB")

    return str(layer_zip_path)


def create_deployment_package(lambda_files, project_name):
    """Create a Lambda function zip (handler code only) plus a matching Lambda Layer zip
    (this member's dependencies), meant to be attached to the function via `layers = [...]`.
    """

    # Paths
    current_dir = Path(__file__).parent
    workspace_root = current_dir.parent.parent
    build_dir = current_dir / 'build'
    package_dir = build_dir / 'package'
    zip_path = current_dir / 'lambda_function.zip'

    # Clean up previous builds
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if zip_path.exists():
        os.remove(zip_path)

    # Create build directory
    package_dir.mkdir(parents=True, exist_ok=True)

    create_layer_package(project_name, build_dir, workspace_root)

    # Copy Lambda function code
    print("Copying Lambda function code...")

    # Copy Lambda handlers & modules
    for file in lambda_files:
        if (current_dir / file).exists():
            shutil.copy(current_dir / file, package_dir)

    # Create ZIP file
    print("Creating deployment package...")
    _zip_dir(package_dir, zip_path)

    # Clean up build directory
    shutil.rmtree(build_dir)

    # Get file size
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"\n✅ Deployment package created: {zip_path}")
    print(f"   Size: {size_mb:.2f} MB")

    if size_mb > 50:
        print("⚠️  Warning: Package exceeds 50MB. Consider using Lambda Layers.")

    return str(zip_path)

if __name__ == '__main__':
    lambda_files = ['dyndb_load_json.py']
    create_deployment_package(lambda_files, project_name='dyndb-load-json')
