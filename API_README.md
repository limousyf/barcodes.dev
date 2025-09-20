# Barcode Generator API Documentation

This document describes the REST API endpoints for generating barcodes and QR codes programmatically.

## Base URL

- **Local Development**: `http://localhost:8080`
- **Production**: `http://your-production-domain:8080`

## Authentication

No authentication required. All endpoints are publicly accessible.

## Content Types

Both endpoints accept:
- `application/json` (JSON request body)
- `application/x-www-form-urlencoded` (form data)

## API Endpoints

### 1. Barcode Generation

Generate various types of barcodes programmatically.

**Endpoint**: `POST /api/barcode`

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `text` | string | ✅ Yes | - | The text/data to encode in the barcode |
| `barcode_type` | string | No | `code128` | Type of barcode to generate |
| `image_format` | string | No | `PNG` | Output image format |

#### Valid Barcode Types

- `code128` - Code 128 (default)
- `code39` - Code 39
- `ean` - European Article Number
- `ean13` - EAN-13
- `ean8` - EAN-8
- `upc` - Universal Product Code
- `upca` - UPC-A
- `isbn` - International Standard Book Number
- `isbn10` - ISBN-10
- `isbn13` - ISBN-13
- `issn` - International Standard Serial Number
- `itf` - Interleaved 2 of 5
- `gs1` - GS1
- `gs1_128` - GS1-128
- `codabar` - Codabar
- `pzn` - Pharmazentralnummer
- `jan` - Japanese Article Number
- `ean14` - EAN-14
- `gtin` - Global Trade Item Number

#### Valid Image Formats

- `PNG` (default)
- `JPEG`
- `WEBP`

#### Example Requests

**JSON Request**:
```bash
curl -X POST http://localhost:8080/api/barcode \
  -H "Content-Type: application/json" \
  -d '{
    "text": "123456789012",
    "barcode_type": "code128",
    "image_format": "PNG"
  }' \
  --output barcode.png
```

**Form Data Request**:
```bash
curl -X POST http://localhost:8080/api/barcode \
  -d "text=123456789012" \
  -d "barcode_type=ean13" \
  -d "image_format=JPEG" \
  --output barcode.jpg
```

**JavaScript Example**:
```javascript
const response = await fetch('/api/barcode', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    text: '123456789012',
    barcode_type: 'code128',
    image_format: 'PNG'
  })
});

if (response.ok) {
  const blob = await response.blob();
  // Use the blob to display or download the image
} else {
  const error = await response.json();
  console.error('Error:', error);
}
```

### 2. QR Code Generation

Generate QR codes with advanced customization options.

**Endpoint**: `POST /api/qrcode`

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `text` | string | ✅ Yes | - | The text/data to encode in the QR code |
| `error_correction` | string | No | `M` | Error correction level |
| `image_format` | string | No | `PNG` | Output image format |
| `fill_color` | string | No | `#000000` | Foreground color (hex format) |
| `back_color` | string | No | `#ffffff` | Background color (hex format) |
| `box_size` | integer | No | `10` | Size of each box in pixels |
| `border` | integer | No | `4` | Border size in boxes |

#### Valid Error Correction Levels

- `L` - Low (~7% correction)
- `M` - Medium (~15% correction) (default)
- `Q` - Quartile (~25% correction)
- `H` - High (~30% correction)

#### Valid Image Formats

- `PNG` (default)
- `JPEG`
- `WEBP`

#### Parameter Constraints

- `box_size`: 1-50 pixels
- `border`: 0-20 boxes
- `fill_color`, `back_color`: Valid hex colors (e.g., `#000000`)

#### Example Requests

**JSON Request**:
```bash
curl -X POST http://localhost:8080/api/qrcode \
  -H "Content-Type: application/json" \
  -d '{
    "text": "https://example.com",
    "error_correction": "M",
    "image_format": "PNG",
    "fill_color": "#000000",
    "back_color": "#ffffff",
    "box_size": 10,
    "border": 4
  }' \
  --output qrcode.png
```

**Form Data Request**:
```bash
curl -X POST http://localhost:8080/api/qrcode \
  -d "text=Hello World" \
  -d "error_correction=H" \
  -d "fill_color=#ff0000" \
  -d "back_color=#ffff00" \
  -d "box_size=15" \
  --output qrcode.png
```

**JavaScript Example**:
```javascript
const response = await fetch('/api/qrcode', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    text: 'https://example.com',
    error_correction: 'H',
    image_format: 'PNG',
    fill_color: '#0066cc',
    back_color: '#ffffff',
    box_size: 12,
    border: 2
  })
});

if (response.ok) {
  const blob = await response.blob();
  // Use the blob to display or download the image
} else {
  const error = await response.json();
  console.error('Error:', error);
}
```

## Response Formats

### Success Response

On successful generation, the API returns the image file directly with appropriate MIME type:

- **Status Code**: `200 OK`
- **Content-Type**: `image/png`, `image/jpeg`, or `image/webp`
- **Body**: Binary image data

### Error Responses

All error responses return JSON with the following structure:

```json
{
  "error": "Error type",
  "message": "Detailed error description",
  "provided": "invalid_value"  // For validation errors
}
```

#### Common Error Status Codes

- **400 Bad Request**: Invalid parameters or validation errors
- **500 Internal Server Error**: Generation failed

#### Example Error Responses

**Missing Required Parameter**:
```json
{
  "error": "Missing required parameter: text",
  "message": "The text parameter is required and cannot be empty"
}
```

**Invalid Barcode Type**:
```json
{
  "error": "Invalid barcode_type",
  "message": "barcode_type must be one of: code128, code39, ean, ean13, ean8, upc, upca, isbn, isbn10, isbn13, issn, itf, gs1, gs1_128, codabar, pzn, jan, ean14, gtin",
  "provided": "invalid_type"
}
```

**Invalid Color Format**:
```json
{
  "error": "Invalid fill_color",
  "message": "fill_color must be a valid hex color (e.g., #000000)",
  "provided": "red"
}
```

## Usage Examples

### Python

```python
import requests

# Generate barcode
response = requests.post('http://localhost:8080/api/barcode', json={
    'text': '123456789012',
    'barcode_type': 'ean13',
    'image_format': 'PNG'
})

if response.status_code == 200:
    with open('barcode.png', 'wb') as f:
        f.write(response.content)
else:
    print('Error:', response.json())

# Generate QR code
response = requests.post('http://localhost:8080/api/qrcode', json={
    'text': 'https://example.com',
    'error_correction': 'H',
    'fill_color': '#0066cc',
    'back_color': '#ffffff'
})

if response.status_code == 200:
    with open('qrcode.png', 'wb') as f:
        f.write(response.content)
else:
    print('Error:', response.json())
```

### Node.js

```javascript
const fs = require('fs');
const fetch = require('node-fetch');

async function generateBarcode() {
  try {
    const response = await fetch('http://localhost:8080/api/barcode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: '123456789012',
        barcode_type: 'code128',
        image_format: 'PNG'
      })
    });

    if (response.ok) {
      const buffer = await response.buffer();
      fs.writeFileSync('barcode.png', buffer);
      console.log('Barcode saved successfully');
    } else {
      const error = await response.json();
      console.error('Error:', error);
    }
  } catch (err) {
    console.error('Request failed:', err);
  }
}

generateBarcode();
```

### PHP

```php
<?php
// Generate barcode
$data = json_encode([
    'text' => '123456789012',
    'barcode_type' => 'ean13',
    'image_format' => 'PNG'
]);

$context = stream_context_create([
    'http' => [
        'method' => 'POST',
        'header' => 'Content-Type: application/json',
        'content' => $data
    ]
]);

$response = file_get_contents('http://localhost:8080/api/barcode', false, $context);

if ($response !== false) {
    file_put_contents('barcode.png', $response);
    echo "Barcode saved successfully\n";
} else {
    echo "Error generating barcode\n";
}
?>
```

## Rate Limiting

Currently, there are no rate limits imposed on the API endpoints. However, please use the API responsibly to ensure availability for all users.

## Support

For issues or questions about the API, please check the main application logs or contact the system administrator.