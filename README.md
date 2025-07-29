# TRP Backend - Property API

A FastAPI-based backend service for the Toronto Regional Real Estate Board (TRP) property management system. This API provides endpoints for property search, user cart/wishlist management, and MLS integration.

## Features

- **Property Search**: Search and filter rental properties from MLS
- **User Authentication**: JWT-based authentication with Supabase
- **Cart Management**: Add/remove properties to user cart
- **Wishlist Management**: Save favorite properties
- **MLS Integration**: Real-time data from Toronto Regional Real Estate Board
- **Async Performance**: Built with FastAPI for high-performance async operations

## API Endpoints

### Properties
- `GET /properties` - Search properties with filters
  - Query parameters: `city`, `property_type`, `min_price`, `max_price`, `bedrooms`, `bathrooms`
  - Returns: List of properties with pagination
- `GET /properties/{property_id}` - Get detailed property information
  - Returns: Detailed property data with description and media

### Cart (Authenticated)
- `GET /cart` - List user's cart items
- `POST /cart/{property_id}` - Add property to cart
- `DELETE /cart/{property_id}` - Remove property from cart

### Wishlist (Authenticated)
- `GET /wishlist` - List user's wishlist
- `POST /wishlist/{property_id}` - Add property to wishlist
- `DELETE /wishlist/{property_id}` - Remove property from wishlist

## Setup

### Prerequisites
- Python 3.8+
- MLS API access credentials
- Supabase account (for authentication and data storage)

### Environment Variables
Create a `.env` file with the following variables:

```env
# MLS API Configuration
MLS_API_URL=your_mls_api_url
MLS_AUTH_TOKEN=your_mls_auth_token

# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_JWT_SECRET=your_jwt_secret

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

### Installation

1. Clone the repository:
```bash
git clone https://github.com/TRP123-beast/trp-backend-new.git
cd trp-backend-new
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run the application:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## Development

### Project Structure
```
├── app/
│   ├── __init__.py
│   ├── auth/
│   │   └── deps.py              # Authentication dependencies
│   ├── property/
│   │   ├── __init__.py
│   │   ├── api.py               # Property endpoints
│   │   ├── cart.py              # Cart management
│   │   ├── wishlist.py          # Wishlist management
│   │   ├── models.py            # Pydantic models
│   │   ├── services.py          # Business logic
│   │   └── clients.py           # External API clients
│   └── user/
├── main.py                      # FastAPI application entry point
├── requirements.txt             # Python dependencies
└── README.md
```

### API Documentation
Once the server is running, visit:
- Interactive API docs: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

### Running Tests
```bash
pytest
```

## Configuration

### MLS API Integration
The application integrates with the Toronto Regional Real Estate Board MLS API using OData protocol. Configure the following:
- `MLS_API_URL`: Base URL for the MLS API
- `MLS_AUTH_TOKEN`: JWT token for API authentication

### Authentication
Uses Supabase for user authentication and data storage:
- JWT token validation
- User session management
- Development mode available for local testing

### CORS
CORS is configured to allow requests from common development origins. Update in `main.py` for production deployment.

## Deployment

### Production Considerations
- Set proper environment variables
- Configure CORS for your domain
- Use a production ASGI server (uvicorn, gunicorn)
- Set up proper logging
- Configure rate limiting if needed

### Docker Support
```bash
# Build image
docker build -t trp-backend .

# Run container
docker run -p 8000:8000 --env-file .env trp-backend
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions or support, please open an issue in the GitHub repository.
