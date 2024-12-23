from kubernetes import client, config
import subprocess
import logging
from typing import List


def get_cluster_name() -> str:
    result = subprocess.run(
        ["kubectl", "config", "current-context"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if result.returncode != 0:
        logging.error(f"Error getting cluster name: {result.stderr}")
        return "unknown_cluster"
    return result.stdout.strip().replace(":", "_").replace("/", "_")


def get_all_distinct_images():
    # Load the kubeconfig file
    config.load_kube_config()

    # Initialize the Kubernetes client
    v1 = client.CoreV1Api()

    # Get all the pods in the cluster
    ret = v1.list_pod_for_all_namespaces(watch=False)

    # Set to store unique images
    unique_images = set()

    for i in ret.items:
        containers = i.spec.containers
        for container in containers:
            image = container.image
            image = image+";"+container.name
            unique_images.add(image)

    return list(unique_images)


def filter_images(images: List[str], substrings: List[str]) -> List[str]:
    return [image for image in images if not any(substring in image for substring in substrings)]


def check_trivy_installed() -> bool:
    result = subprocess.run(
        ["trivy", "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return result.returncode == 0
