## Deploying

First create the necessary secrets for database and admin token access. Replace the placeholders with your actual values.
```bash
kubectl -n wynnsource-dev create secret generic wynnsource-secrets \
  --from-literal=WCS_ADMIN_TOKEN='<your-admin-token>'
```
Or you can use sealed secrets for better security.

Then use this as an example to deploy the application using ArgoCD.
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: wynnsource-dev
  namespace: argocd
spec:
  project: default
  source:
    repoURL: git@github.com:WynnSource/WynnSourceServer.git
    targetRevision: dev
    path: deploy
  destination:
    server: https://kubernetes.default.svc
    namespace: wynnsource-dev
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```
You have to add your ingress configuration as well, 
also make sure there is the `X-Real-IP` header from the ingress controller for proper client IP logging and rate limiting.

## License

`Copyright (C) <2026>  <FYWinds>`

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-v3) with the following [**Exception**](#exception-for-generated-client-code).

### Exception for Generated Client Code
As a special exception to the AGPL-v3, the copyright holders of this library give you permission to generate, use, distribute, and license the client libraries (SDKs) generated from this project's API specifications (e.g., OpenAPI/Swagger documents, Protocol Buffers, GraphQL schemas) under any license of your choice, including proprietary licenses. This exception does not apply to the backend logic itself.

### Reason
We've considered the implications of the AGPL-v3 and have decided to apply it to the backend logic of this project to ensure that any modifications to the server-side code are shared with the community. However, we recognize that client libraries generated from our API specifications may be used in a wide variety of applications, including minecraft mods, which may not be compatible with the AGPL-v3. By granting this exception, we aim to encourage the use of our API and allow developers to create client libraries without worrying about licensing issues, while still ensuring that contributions to the server-side code are shared with the community.