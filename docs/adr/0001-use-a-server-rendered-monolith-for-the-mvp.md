# Use a server-rendered monolith for the MVP

The MVP will use one Python web application to render HTML and handle Task operations, with lightweight progressive enhancement rather than a separate single-page frontend and API. This keeps deployment, state management, validation, and testing inside one application boundary while preserving responsive interactions; a separate frontend can be introduced later if product needs justify the additional contract and build complexity.
