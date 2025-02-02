import logging
import copy
from datetime import datetime
from colorama import Fore
from utils import get_cluster_name, check_trivy_installed, get_all_distinct_images
from scan import scan_image
from sqs import send_to_input_sqs

# Set up logging
scan_timestamp = datetime.now().strftime("%Y%m%d-%H%M")
log_filename = f"scan_log_{scan_timestamp}.log"
logging.basicConfig(filename=log_filename, level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(message)s')


def prompt_user(cluster_name):
    print(f"\nCluster Name: {cluster_name}")
    response = input(
        "Do you want to scan the current cluster content? (yes/no): ").strip().lower()
    return response == 'yes'



def main() -> None:
    print(f"{Fore.CYAN}Kubernetes CVE Scanner by ZERODOTFIVE Hamburg GmbH - moin@zerodotfive.com")
    if not check_trivy_installed():
        print(f"{Fore.RED}Trivy is not installed or not found in PATH. Please install Trivy to proceed.{Fore.RESET}")
        return

    cluster_name = get_cluster_name()

    if not prompt_user(cluster_name):
        print("Scan aborted.")
        return

    images = get_all_distinct_images()

    for image in images:
        if "sha256" in image:
            logging.info(f"Skipped image: {image}")
            continue
        image_container = image.split(";")

        image = image_container[0]
        container = image_container[1]
        try:
            logging.info(f"Scanning image: {image}")
            scan_result, error_message = scan_image(image)

            if len(scan_result['Results']) > 0:
                all_vulnerabilities = []
                for result in scan_result['Results']:
                    single_scan_result = copy.deepcopy(scan_result)
                    single_scan_result['Results'] = [result]

                    vulnerabilities = result.get('Vulnerabilities', [])
                    
                    # Enrich vulnerabilities with EPSS scores
                    for vuln in vulnerabilities:
                        single_vulnerability = copy.deepcopy(single_scan_result)
                        single_vulnerability['Results'][0]['Vulnerabilities'] = [vuln]
                        single_vulnerability['Results'][0]['References'] = []

                        # Send each vulnerability to SQS
                        send_to_input_sqs(container_name=container, scan_payload=single_vulnerability)

                    all_vulnerabilities.extend(vulnerabilities)

                summary = {
                    'image': f"image:{image}",
                    'total': len(all_vulnerabilities),
                    'high': len([v for v in all_vulnerabilities if v['Severity'].upper() == 'HIGH']),
                    'critical': len([v for v in all_vulnerabilities if v['Severity'].upper() == 'CRITICAL']),
                    'medium': len([v for v in all_vulnerabilities if v['Severity'].upper() == 'MEDIUM']),
                    'low': len([v for v in all_vulnerabilities if v['Severity'].upper() == 'LOW']),
                }

                print(
                    f"{Fore.CYAN}Summary for image: {image}: {Fore.RESET}Total: {summary['total']}, "
                    f"{Fore.LIGHTRED_EX}High: {summary['high']}, "
                    f"{Fore.RED}Critical: {summary['critical']}, "
                    f"{Fore.YELLOW}Medium: {summary['medium']}, "
                    f"{Fore.GREEN}Low: {summary['low']}"
                    )
            else:
                print(f"Scanning {image} error")
                error_message = f"Failed to scan image: {image}\n{error_message}\n"
                logging.error(error_message)
        except Exception as e:
            error_message = f"Exception occurred while scanning image: {image}\n{str(e)}\n"
            print(e)


if __name__ == "__main__":
    main()
