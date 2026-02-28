## Deploying

First create the necessary secrets for database and admin token access. Replace the placeholders with your actual values.
```bash
kubectl -n wynnsource-dev create secret generic wynnsource-secrets \
  --from-literal=WCS_DB_POSTGRES_DSN='postgresql+asyncpg://wynnsource:<password>@wynnsource-pg-rw:5432/wcs_db' \
  --from-literal=WCS_DB_REDIS_DSN='redis://wynnsource-redis:6379/0' \
  --from-literal=WCS_ADMIN_TOKEN='<your-admin-token>'
```

## License

`Copyright (C) <2026>  <FYWinds>`

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-v3) with the following [**Exception**](#exception-for-generated-client-code).

### Exception for Generated Client Code
As a special exception to the AGPL-v3, the copyright holders of this library give you permission to generate, use, distribute, and license the client libraries (SDKs) generated from this project's API specifications (e.g., OpenAPI/Swagger documents, Protocol Buffers, GraphQL schemas) under any license of your choice, including proprietary licenses. This exception does not apply to the backend logic itself.

### Reason
We've considered the implications of the AGPL-v3 and have decided to apply it to the backend logic of this project to ensure that any modifications to the server-side code are shared with the community. However, we recognize that client libraries generated from our API specifications may be used in a wide variety of applications, including minecraft mods, which may not be compatible with the AGPL-v3. By granting this exception, we aim to encourage the use of our API and allow developers to create client libraries without worrying about licensing issues, while still ensuring that contributions to the server-side code are shared with the community.