## Disclaimer and security requirements

This project is an independent data export utility and is not affiliated
with, maintained by, or endorsed by the antivirus vendor.

Users are responsible for ensuring that their use of this software complies
with the antivirus vendor's license terms, applicable laws, organizational
security policies, and data protection requirements.

For security reasons, users should:

- create a dedicated technical database account for this script;
- grant the account only the minimum read-only permissions required to access
  the necessary tables or views;
- not use administrator, database owner, or personal user accounts;
- run the script only from a dedicated, controlled machine;
- configure database firewall or ACL rules to allow connections only from that
  machine or its explicitly assigned IP address;
- store database credentials securely and never commit them to the repository;
- protect generated Excel files because they may contain sensitive
  infrastructure, host, user, or security-status information;
- regularly review and revoke permissions that are no longer required.

Users are solely responsible for properly configuring database access,
network restrictions, credential storage, and protection of exported data.
The authors are not responsible for unauthorized access, data disclosure,
data loss, or other consequences resulting from improper deployment or
configuration.
