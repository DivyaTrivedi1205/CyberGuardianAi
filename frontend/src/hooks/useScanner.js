import { useState } from 'react';
import { apiRequest } from '../api/client';

export function useScanner(apiPath, defaultMethod = 'POST') {
  const [input, setInput] = useState('');
  const [result, setResult] = useState(null);
  const [isScanning, setIsScanning] = useState(false);
  const [history, setHistory] = useState([]);

  const scan = async (payload, asFormData = false) => {
    setIsScanning(true);
    try {
      const options = {
        method: defaultMethod,
      };

      if (asFormData) {
        options.body = payload;
        // Fetch automatically sets the correct multipart boundary if Content-Type is omitted.
        // We delete it if it was previously set globally or by our client wrapper.
        options.headers = { 'Content-Type': undefined };
      } else {
        options.body = JSON.stringify(payload);
      }

      const res = await apiRequest(apiPath, options);
      
      // Update result correctly allowing unified assessment blocks
      setResult(res);
      return res;
    } catch (error) {
      console.error(`Failed to analyze via ${apiPath}:`, error);
      // Construct a generic fallback error directly on the result block
      const fallbackResult = {
        prediction: 'Legitimate',
        risk_score: 15,
        features: {},
        feedback: ['Error performing backend scan. Displaying local fallback safe status.', error.message]
      };
      setResult(fallbackResult);
      return fallbackResult;
    } finally {
      setIsScanning(false);
    }
  };

  const fetchHistory = async (historyPath) => {
    try {
      const res = await apiRequest(historyPath);
      setHistory(res || []);
    } catch (error) {
      console.error(`Failed to fetch history from ${historyPath}:`, error);
    }
  };

  return {
    input, setInput,
    result, setResult,
    isScanning,
    history, setHistory,
    scan,
    fetchHistory
  };
}
