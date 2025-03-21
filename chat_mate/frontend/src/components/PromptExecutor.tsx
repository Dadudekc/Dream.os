import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Input,
  Slider,
  SliderFilledTrack,
  SliderThumb,
  SliderTrack,
  Text,
  Textarea,
  VStack,
  useToast
} from '@chakra-ui/react';
import React, { useState } from 'react';

import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface PromptExecutorProps {
  onResponse?: (response: any) => void;
}

export const PromptExecutor: React.FC<PromptExecutorProps> = ({ onResponse }) => {
  const [prompt, setPrompt] = useState('');
  const [temperature, setTemperature] = useState(0.7);
  const [isLoading, setIsLoading] = useState(false);
  const toast = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_URL}/api/v1/prompts/execute`, {
        prompt_text: prompt,
        temperature,
        model: 'gpt-4'
      });

      if (onResponse) {
        onResponse(response.data);
      }

      toast({
        title: 'Success',
        description: 'Prompt executed successfully',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to execute prompt',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Box as="form" onSubmit={handleSubmit} width="100%" maxW="800px" p={4}>
      <VStack spacing={4} align="stretch">
        <FormControl isRequired>
          <FormLabel>Prompt</FormLabel>
          <Textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Enter your prompt here..."
            minH="200px"
          />
        </FormControl>

        <FormControl>
          <FormLabel>Temperature: {temperature}</FormLabel>
          <Slider
            value={temperature}
            onChange={setTemperature}
            min={0}
            max={1}
            step={0.1}
          >
            <SliderTrack>
              <SliderFilledTrack />
            </SliderTrack>
            <SliderThumb />
          </Slider>
        </FormControl>

        <Button
          type="submit"
          colorScheme="blue"
          isLoading={isLoading}
          loadingText="Executing..."
        >
          Execute Prompt
        </Button>
      </VStack>
    </Box>
  );
}; 