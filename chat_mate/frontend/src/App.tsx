import { ChakraProvider, Container, Heading, Tab, TabList, TabPanel, TabPanels, Tabs, VStack } from '@chakra-ui/react';

import { DiscordManager } from './components/DiscordManager';
import { PromptExecutor } from './components/PromptExecutor';
import React from 'react';

function App() {
  return (
    <ChakraProvider>
      <Container maxW="container.xl" py={8}>
        <VStack spacing={8} align="stretch">
          <Heading as="h1" size="xl" textAlign="center">
            Dreamscape Beta Dashboard
          </Heading>

          <Tabs variant="enclosed">
            <TabList>
              <Tab>Prompt Executor</Tab>
              <Tab>Discord Manager</Tab>
            </TabList>

            <TabPanels>
              <TabPanel>
                <PromptExecutor />
              </TabPanel>
              <TabPanel>
                <DiscordManager />
              </TabPanel>
            </TabPanels>
          </Tabs>
        </VStack>
      </Container>
    </ChakraProvider>
  );
}

export default App; 