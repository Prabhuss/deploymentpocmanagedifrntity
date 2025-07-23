from flask import Flask, request, jsonify
from azure.identity import DefaultAzureCredential
from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import BlobServiceClient
import os
from dotenv import load_dotenv

# Load .env values (for local dev)
load_dotenv()

app = Flask(__name__)

# Azure Credentials
credential = DefaultAzureCredential()

SUBSCRIPTION_ID = os.environ.get("AZURE_SUBSCRIPTION_ID")
RESOURCE_GROUP = os.environ.get("AZURE_RESOURCE_GROUP")

if not SUBSCRIPTION_ID or not RESOURCE_GROUP:
    raise Exception("AZURE_SUBSCRIPTION_ID and AZURE_RESOURCE_GROUP must be set.")

# Debug Logger
def log_request_details():
    print(f"Request method: {request.method}")
    print(f"Request headers: {dict(request.headers)}")
    print(f"Request body: {request.get_data(as_text=True)}")

# Health Check Endpoint (POST)
@app.route("/ping", methods=["POST"])
def ping():
    log_request_details()
    return jsonify({"message": "POST is working", "data": request.json}), 200

# 1. List Storage Accounts
@app.route("/storage-accounts", methods=["GET"])
def list_storage_accounts():
    try:
        log_request_details()
        storage_client = StorageManagementClient(credential, SUBSCRIPTION_ID)
        accounts = storage_client.storage_accounts.list_by_resource_group(RESOURCE_GROUP)
        return jsonify([acct.name for acct in accounts])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 2. Create a Storage Account (with trailing slash support)
@app.route("/storage-accounts/create", methods=["POST"])
@app.route("/storage-accounts/create/", methods=["POST"])
def create_storage_account():
    try:
        log_request_details()
        data = request.json
        account_name = data.get("account_name")

        if not account_name:
            return jsonify({"error": "account_name is required"}), 400

        storage_client = StorageManagementClient(credential, SUBSCRIPTION_ID)
        params = {
            "sku": {"name": "Standard_LRS"},
            "kind": "StorageV2",
            "location": "centralindia",
        }

        poller = storage_client.storage_accounts.begin_create(
            RESOURCE_GROUP, account_name, params
        )
        account = poller.result()
        return jsonify({"status": "created", "name": account.name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 3. List Blobs in a Container
@app.route("/storage-accounts/blobs", methods=["GET"])
def list_blobs():
    try:
        log_request_details()
        account_name = request.args.get("account_name")
        container_name = request.args.get("container_name")

        if not account_name or not container_name:
            return jsonify({"error": "account_name and container_name are required"}), 400

        blob_service = BlobServiceClient(
            f"https://{account_name}.blob.core.windows.net", credential
        )
        container_client = blob_service.get_container_client(container_name)
        blobs = [blob.name for blob in container_client.list_blobs()]
        return jsonify(blobs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def home():
    return "Flask Managed Identity Test API is running."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 6000))
    app.run(host="0.0.0.0", port=port)
