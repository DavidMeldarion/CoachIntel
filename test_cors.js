// Test script to simulate browser CORS behavior
const data = {
  first_name: "David",
  last_name: "Cunningham", 
  phone: "123-456-7890",
  address: "123 Test St"
};

// Simulate the browser API call with credentials
fetch('http://localhost:8000/user', {
  method: 'PUT',
  headers: {
    'Content-Type': 'application/json',
    'Cookie': 'user=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlaWZ0c2FzZmNAZ21haWwuY29tIiwiZXhwIjoxNzUyMTQ0NjQzfQ.xOKNFp_N9hxKb02qorJ7ZJsO0c5Qq_vJLdFYW8uFxYA'
  },
  credentials: 'include',
  body: JSON.stringify(data)
})
.then(response => {
  console.log('Response status:', response.status);
  console.log('Response headers:', [...response.headers.entries()]);
  return response.json();
})
.then(data => console.log('Response data:', data))
.catch(error => console.error('Error:', error));
