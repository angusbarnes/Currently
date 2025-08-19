import os
import json
import hashlib
import gnupg
import getpass
import argparse
from pathlib import Path


# Configuration
# TODO FIX THIS GARBAGE
SENSITIVE_DIR = "sensitive_data"  # Directory with gitignored sensitive files
BUNDLE_FILE = "sensitive_bundle.gpg"  # Encrypted bundle
METADATA_FILE = "sensitive_metadata.json"  # Metadata file tracking file hashes

gpg = None


def hash_file(filepath):
    """Returns SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()


def load_metadata():
    """Load the metadata JSON file."""
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    return {}


def save_metadata(metadata):
    """Save the metadata JSON file."""
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=4)


def scan_sensitive_files():
    """Scan the sensitive directory for files and check for changes."""
    metadata = load_metadata()
    changes = []

    for root, _, files in os.walk(SENSITIVE_DIR):
        for file in files:
            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, SENSITIVE_DIR)
            file_hash = hash_file(filepath)

            if rel_path not in metadata:
                print(f"[NEW] {rel_path} detected.")
                changes.append((rel_path, file_hash))
            elif metadata[rel_path] != file_hash:
                choice = input(f"[MODIFIED] {rel_path} changed. Update? (y/n): ")
                if choice.lower() == "y":
                    changes.append((rel_path, file_hash))

    for rel_path, file_hash in changes:
        metadata[rel_path] = file_hash

    save_metadata(metadata)
    return changes


def bundle_files():
    """Encrypt and bundle files into a single encrypted archive."""
    changes = scan_sensitive_files()
    if not changes:
        print("No changes detected. Skipping bundling.")
        return

    archive_content = {}
    for rel_path, _ in changes:
        full_path = os.path.join(SENSITIVE_DIR, rel_path)
        with open(full_path, "rb") as f:
            archive_content[rel_path] = f.read()

    # Serialize archive as JSON (binary-encoded data)
    archive_json = json.dumps(archive_content, indent=4)
    password = getpass.getpass("Enter encryption password: ")
    encrypted_data = gpg.encrypt(archive_json, symmetric=True, passphrase=password)

    with open(BUNDLE_FILE, "wb") as f:
        f.write(str(encrypted_data).encode())
    print(f"Sensitive files bundled into {BUNDLE_FILE}")


def unpack_files():
    """Decrypt and restore files to their original locations."""
    if not os.path.exists(BUNDLE_FILE):
        print("No bundle found.")
        return

    password = getpass.getpass("Enter decryption password: ")
    with open(BUNDLE_FILE, "rb") as f:
        decrypted_data = gpg.decrypt(f.read(), passphrase=password)

    if not decrypted_data:
        print("Decryption failed. Incorrect password?")
        return

    archive_content = json.loads(str(decrypted_data))
    for rel_path, file_data in archive_content.items():
        file_path = os.path.join(SENSITIVE_DIR, rel_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(file_data.encode())
        print(f"Restored {rel_path}")


def main():

    # Configuration
    # TODO FIX THIS GARBAGE
    SENSITIVE_DIR = "sensitive_data"  # Directory with gitignored sensitive files
    BUNDLE_FILE = "sensitive_bundle.gpg"  # Encrypted bundle
    METADATA_FILE = "sensitive_metadata.json"  # Metadata file tracking file hashes
    parser = argparse.ArgumentParser(description="Secure file bundler")
    parser.add_argument(
        "command", choices=["bundle", "unpack"], help="Command to execute"
    )
    parser.add_argument(
        "--dir", default=SENSITIVE_DIR, help="Directory containing sensitive files"
    )
    parser.add_argument("--bundle", default=BUNDLE_FILE, help="Encrypted bundle file")
    parser.add_argument(
        "--metadata", default=METADATA_FILE, help="Metadata tracking file"
    )

    args = parser.parse_args()

    SENSITIVE_DIR = args.dir
    BUNDLE_FILE = args.bundle
    METADATA_FILE = args.metadata

    if args.command == "bundle":
        bundle_files()
    elif args.command == "unpack":
        unpack_files()


if __name__ == "__main__":
    main()
