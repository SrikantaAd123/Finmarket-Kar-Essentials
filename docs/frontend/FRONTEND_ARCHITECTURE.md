
# Frontend Architecture

## 1. Overview

The Finmarket Kart Essentials frontend provides the user interface for the e-commerce application.

It is organized into HTML templates, reusable components, CSS stylesheets, images, fonts, and JavaScript modules.

The frontend is responsible for presenting products, managing user interactions, communicating with backend APIs, and supporting shopping workflows.

The main frontend technologies are:

- HTML for page structure.
- CSS for styling and responsive layouts.
- JavaScript for application behavior and user interactions.
- FastAPI backend APIs for application data and business operations.

## 2. Frontend Directory Structure

The frontend directory is organized as follows:

```text
frontend/
├── components/
│   ├── footer.html
│   ├── navbar.html
│   ├── product_card.html
│   └── sidebar.html
│
├── static/
│   ├── css/
│   │   ├── admin.css
│   │   ├── base.css
│   │   ├── components.css
│   │   ├── responsive.css
│   │   ├── store.css
│   │   └── theme.css
│   │
│   ├── fonts/
│   │
│   ├── images/
│   │   ├── banners/
│   │   ├── logo/
│   │   └── products/
│   │
│   └── js/
│       ├── admin.js
│       ├── api.js
│       ├── app.js
│       ├── auth.js
│       ├── cart.js
│       ├── catalog.js
│       ├── checkout.js
│       └── orders.js
│
└── templates/
    ├── account.html
    ├── admin.html
    ├── cart.html
    ├── checkout.html
    ├── index.html
    ├── login.html
    ├── orders.html
    └── product.html
```

## 3. Frontend Components

The `components/` directory contains reusable HTML components.

These components help maintain consistent page layouts and reduce repeated markup.

### 3.1 footer.html

The footer component represents the bottom section of the website.

It can contain:

- Company information.
- Contact information.
- Navigation links.
- Copyright information.
- Additional website links.

### 3.2 navbar.html

The navigation bar provides the primary navigation interface.

It can contain:

- Website logo.
- Home navigation.
- Product navigation.
- Account access.
- Shopping cart access.
- Other primary navigation links.

### 3.3 product_card.html

The product card represents an individual product in product listings.

It can display:

- Product image.
- Product name.
- Product price.
- Product description.
- Product availability.
- Product navigation or action controls.

### 3.4 sidebar.html

The sidebar provides additional navigation or filtering options.

It can be used for:

- Product categories.
- Product filters.
- Administrative navigation.
- Additional application sections.

## 4. Static Assets

The `static/` directory stores frontend resources such as stylesheets, images, fonts, and JavaScript files.

### 4.1 CSS Directory

The `static/css/` directory contains the application's stylesheets.

#### base.css

Contains common foundational styles used throughout the frontend.

Examples include:

- Default typography.
- Common element styling.
- Shared layout rules.
- General spacing.

#### theme.css

Contains visual theme-related styling.

Examples include:

- Theme colors.
- Background colors.
- Text colors.
- Visual design variables.

#### components.css

Contains styling for reusable frontend components.

Examples include:

- Navigation bar styling.
- Footer styling.
- Product card styling.
- Sidebar styling.
- Buttons and shared interface elements.

#### responsive.css

Contains responsive layout rules for different screen sizes.

It can define:

- Mobile layouts.
- Tablet layouts.
- Desktop layouts.
- Responsive navigation.
- Flexible product grids.

#### store.css

Contains styles associated with the shopping and store interface.

Examples include:

- Product listings.
- Store layouts.
- Shopping sections.
- Product display areas.

#### admin.css

Contains styles for administrative interface pages.

Examples include:

- Admin dashboard layouts.
- Management tables.
- Administrative navigation.
- Dashboard components.

### 4.2 Fonts Directory

The `static/fonts/` directory stores font assets used by the frontend.

These assets can be referenced through CSS font declarations.

### 4.3 Images Directory

The `static/images/` directory stores image assets.

It is organized into the following folders:

#### banners/

Stores banner images used for promotional sections and website headers.

#### logo/

Stores website logo assets.

#### products/

Stores product-related images displayed in the catalog and product pages.

## 5. JavaScript Architecture

The `static/js/` directory contains JavaScript modules responsible for frontend functionality.

Each file is organized around a particular application responsibility.

### 5.1 api.js

The API module provides the frontend integration layer for backend communication.

Its responsibilities may include:

- Sending HTTP requests.
- Handling API responses.
- Managing request headers.
- Handling API errors.
- Providing reusable API communication functions.

### 5.2 app.js

The application module coordinates general frontend behavior.

Its responsibilities may include:

- Initializing frontend functionality.
- Registering shared event handlers.
- Coordinating common application interactions.
- Connecting reusable frontend modules.

### 5.3 auth.js

The authentication module manages frontend authentication-related interactions.

Its responsibilities may include:

- Login-related requests.
- Logout-related interactions.
- Authentication state handling.
- Access token handling.
- Authentication-related error handling.

### 5.4 catalog.js

The catalog module handles product catalog interactions.

Its responsibilities may include:

- Loading product information.
- Displaying product listings.
- Handling product categories.
- Applying product filters.
- Supporting product search.

### 5.5 cart.js

The cart module manages shopping cart interactions.

Its responsibilities may include:

- Adding products to the cart.
- Removing products from the cart.
- Updating product quantities.
- Displaying cart information.
- Calculating cart totals using appropriate backend data and validation.

### 5.6 checkout.js

The checkout module manages the checkout interface.

Its responsibilities may include:

- Collecting checkout information.
- Validating user input.
- Submitting checkout requests.
- Handling checkout responses.
- Supporting payment-related interactions.

### 5.7 orders.js

The orders module manages order-related frontend interactions.

Its responsibilities may include:

- Retrieving order information.
- Displaying order details.
- Showing order status.
- Supporting order history.
- Handling order-related actions.

### 5.8 admin.js

The administrative JavaScript module supports admin interface interactions.

Its responsibilities may include:

- Initializing administrative pages.
- Loading dashboard information.
- Supporting management interfaces.
- Handling administrative API requests.

## 6. HTML Templates

The `templates/` directory contains the main HTML pages of the frontend.

Each template represents a specific application page.

### 6.1 index.html

The main landing page of the e-commerce application.

It can display:

- Website navigation.
- Promotional banners.
- Featured products.
- Product categories.
- Store information.

### 6.2 login.html

Provides the login interface for users.

It can contain:

- Login form fields.
- Input validation.
- Authentication controls.
- Error messages.

### 6.3 account.html

Represents the account-related page.

It can provide access to user account information and related account functionality.

### 6.4 product.html

Displays details about an individual product.

It can contain:

- Product image.
- Product name.
- Product description.
- Product price.
- Availability information.
- Add-to-cart functionality.

### 6.5 cart.html

Displays the shopping cart.

It can show:

- Selected products.
- Product quantities.
- Individual prices.
- Cart totals.
- Cart modification controls.

### 6.6 checkout.html

Provides the checkout interface.

It can collect the required checkout information and initiate the checkout workflow.

### 6.7 orders.html

Displays order-related information.

It can provide:

- Order history.
- Order details.
- Order status.
- Order-related actions.

### 6.8 admin.html

Provides the administrative interface.

It can be used for authorized administrative operations and management functionality.

## 7. Frontend and Backend Communication

The frontend communicates with the FastAPI backend through HTTP API requests.

The `api.js` module is intended to provide a reusable integration layer for these requests.

The general communication flow is:

1. A user performs an action on a frontend page.
2. JavaScript handles the user interaction.
3. The frontend prepares the required request.
4. The request is sent to the appropriate backend API endpoint.
5. FastAPI processes the request.
6. The backend returns an API response.
7. JavaScript processes the response.
8. The frontend updates the displayed information.

The frontend should not independently determine sensitive business operations such as payment confirmation or order authorization.

These operations must be validated by the backend.

## 8. Main E-Commerce Workflows

### 8.1 Authentication Workflow

The authentication-related frontend workflow uses:

- `login.html`
- `auth.js`
- `api.js`

The frontend collects login information and communicates with the backend authentication endpoints.

The backend is responsible for validating authentication and enforcing access permissions.

### 8.2 Product Catalog Workflow

The catalog workflow uses:

- `index.html`
- `product.html`
- `product_card.html`
- `catalog.js`
- `api.js`

The frontend retrieves product information and displays the available catalog to users.

### 8.3 Shopping Cart Workflow

The shopping cart workflow uses:

- `cart.html`
- `cart.js`
- `api.js`

Users can interact with selected products and update their cart.

The backend should validate product availability, pricing, and cart-related business rules.

### 8.4 Checkout Workflow

The checkout workflow uses:

- `checkout.html`
- `checkout.js`
- `cart.js`
- `api.js`

The frontend collects checkout information and submits the required request to the backend.

The backend validates the request and processes the checkout operation.

### 8.5 Order Management Workflow

The order workflow uses:

- `orders.html`
- `orders.js`
- `api.js`

The frontend retrieves and displays order information returned by the backend.

### 8.6 Administration Workflow

The administration workflow uses:

- `admin.html`
- `admin.js`
- `admin.css`
- `sidebar.html`

Administrative operations should be protected by backend authentication and authorization checks.

## 9. Responsive Design

The frontend includes `responsive.css` to support different screen sizes.

The responsive design should provide a consistent experience across:

- Desktop computers.
- Laptops.
- Tablets.
- Mobile devices.

Responsive layouts help ensure that navigation, product cards, forms, and other interface elements remain usable on smaller screens.

## 10. Frontend Design Guidelines

The following guidelines help maintain the frontend codebase:

- Keep HTML templates organized by page responsibility.
- Reuse common components where appropriate.
- Keep CSS styles separated by purpose.
- Keep JavaScript modules focused on specific functionality.
- Avoid unnecessary duplication.
- Use consistent naming conventions.
- Validate user input before submitting requests.
- Handle API errors gracefully.
- Keep sensitive business validation in the backend.
- Ensure responsive behavior across supported screen sizes.

## 11. Frontend Maintenance

When modifying the frontend:

1. Identify the relevant HTML template.
2. Identify the related reusable component, if applicable.
3. Check the associated CSS file.
4. Review the relevant JavaScript module.
5. Verify the backend API contract before changing requests.
6. Test the affected user workflow.
7. Check desktop and mobile layouts.
8. Verify that existing functionality remains intact.

## 12. Summary

The Finmarket Kart Essentials frontend is organized into reusable components, HTML templates, static assets, CSS stylesheets, and JavaScript modules.

The architecture separates responsibilities:

- HTML provides page structure.
- Components provide reusable interface elements.
- CSS controls visual presentation and responsive behavior.
- JavaScript manages user interactions and API communication.
- FastAPI handles backend business operations and data processing.

This organization helps maintain a modular and understandable frontend codebase.
