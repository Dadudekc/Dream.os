import {
  Badge,
  Box,
  Button,
  FormControl,
  FormLabel,
  HStack,
  Input,
  Switch,
  Text,
  VStack,
  useToast
} from '@chakra-ui/react';
import React, { useEffect, useState } from 'react';

import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const DiscordManager: React.FC = () => {
  const [config, setConfig] = useState({
    token: '',
    channel_id: '',
    prefix: '!',
    auto_responses: true
  });
  const [status, setStatus] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const toast = useToast();

  const fetchStatus = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/discord/status`);
      setStatus(response.data);
    } catch (error) {
      console.error('Failed to fetch status:', error);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleLaunch = async () => {
    setIsLoading(true);
    try {
      await axios.post(`${API_URL}/api/v1/discord/launch`, config);
      toast({
        title: 'Success',
        description: 'Discord bot launched successfully',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      fetchStatus();
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to launch bot',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleStop = async () => {
    try {
      await axios.post(`${API_URL}/api/v1/discord/stop`);
      toast({
        title: 'Success',
        description: 'Discord bot stopped successfully',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      fetchStatus();
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to stop bot',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  return (
    <Box width="100%" maxW="800px" p={4}>
      <VStack spacing={4} align="stretch">
        {status && (
          <HStack>
            <Text>Status:</Text>
            <Badge colorScheme={status.status === 'running' ? 'green' : 'gray'}>
              {status.status}
            </Badge>
          </HStack>
        )}

        <FormControl>
          <FormLabel>Bot Token</FormLabel>
          <Input
            type="password"
            value={config.token}
            onChange={(e) => setConfig({ ...config, token: e.target.value })}
            placeholder="Enter Discord bot token"
          />
        </FormControl>

        <FormControl>
          <FormLabel>Channel ID</FormLabel>
          <Input
            value={config.channel_id}
            onChange={(e) => setConfig({ ...config, channel_id: e.target.value })}
            placeholder="Enter channel ID"
          />
        </FormControl>

        <FormControl>
          <FormLabel>Command Prefix</FormLabel>
          <Input
            value={config.prefix}
            onChange={(e) => setConfig({ ...config, prefix: e.target.value })}
            placeholder="Enter command prefix"
          />
        </FormControl>

        <FormControl display="flex" alignItems="center">
          <FormLabel mb="0">Auto Responses</FormLabel>
          <Switch
            isChecked={config.auto_responses}
            onChange={(e) => setConfig({ ...config, auto_responses: e.target.checked })}
          />
        </FormControl>

        <HStack spacing={4}>
          <Button
            colorScheme="blue"
            onClick={handleLaunch}
            isLoading={isLoading}
            loadingText="Launching..."
            isDisabled={status?.status === 'running'}
          >
            Launch Bot
          </Button>
          <Button
            colorScheme="red"
            onClick={handleStop}
            isDisabled={status?.status !== 'running'}
          >
            Stop Bot
          </Button>
        </HStack>
      </VStack>
    </Box>
  );
}; 