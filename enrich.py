def enrich_payload(scan_payload, account_id, cluster_name, container_name):
    """
    Enriches the scan payload with additional metadata.

    Parameters:
        scan_payload (dict): The original scan payload to be enriched.
        account_id (str): AWS account ID.
        cluster_name (str): The name of the Kubernetes cluster.
        container_name (str): The name of the container.

    Returns:
        dict: The enriched scan payload.
    """
    enriched_payload = scan_payload.copy()  # Copy the original payload to avoid mutating the input
    enriched_payload.update({
        "DocumentType": "DOCKER_IMAGE",
        "AccountId": account_id,
        "HostSystemName": cluster_name,
        "HostSystemType": "EKS",
        "SystemName": container_name,
        "DocumentVersion": 1
    })

    return enriched_payload
