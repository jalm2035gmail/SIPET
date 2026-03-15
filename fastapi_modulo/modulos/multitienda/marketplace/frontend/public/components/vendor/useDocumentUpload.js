import { useState } from 'react';
import axios from 'axios';

export function useDocumentUpload() {
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState('');

  const handleDocumentUpload = async (type, file, token = null) => {
    setUploading(true);
    setUploadMessage('');
    const formData = new FormData();
    formData.append('document_type', type);
    formData.append('file', file);
    try {
      await axios.post('/api/vendors/upload-document/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        }
      });
      setUploadMessage('Document uploaded successfully');
    } catch (error) {
      setUploadMessage(error.response?.data?.detail || 'Error uploading document');
    } finally {
      setUploading(false);
    }
  };

  return { uploading, uploadMessage, handleDocumentUpload };
}
