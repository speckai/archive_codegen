"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";

const faqList = [
  {
    question: "How do I start a bug report with Speck?",
    answer:
      "The Speck platform opens a hosted instance of your application that you can access from the dashboard. Click the record button and you can start reproducing the bug!",
  },
  {
    question: "Do you integrate with Jira/Linear/Trello/Asana/Monday?",
    answer:
      "Yes, Speck has integrations for tracking tools including Jira, GitHub Issues, Linear, Trello, Asana, Monday and more.",
  },
  {
    question: "What frameworks and libraries does Speck support?",
    answer:
      "Speck is built for React and supports React frameworks like Create React App, Next.js, Vite, Gatsby, Remix, and more.",
  },
  {
    question: "What information does Speck capture during recording?",
    answer:
      "Speck captures browser logs, console logs, network logs and interactions with the site. We also use your interactions to map to the code, so you can figure out exactly what files are causing your bug.",
  },
  {
    question: "Do I need to be technical to use Speck?",
    answer:
      "No! Reporting a bug is as easy as using the site, and Speck automatically generates an issue. Only the code analysis and report attached to the issue is technical.",
  },
  {
    question: "How does Speck access my code?",
    answer:
      "You can give Speck access to your own codebases by adding the Speck GitHub app to your repository. Speck sets up your site and configures settings automatically.",
  },
  {
    question: "How can I get access to Speck?",
    answer: "Speck is available for $80 a month.",
  },
];

export default function Faq() {
  const [openItem, setOpenItem] = useState<string | null>(null);

  const toggleItem = (id: string) => {
    setOpenItem(openItem === id ? null : id);
  };

  return (
    <div className="py-12 px-4 md:px-12 bg-[rgba(255,255,255,0.02)] border-t border-b border-[rgba(255,255,255,0.1)]">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-4xl mb-4 font-bold text-center">
          Frequently Asked Questions
        </h2>

        <div className="w-full">
          {faqList.map((faq, index) => {
            const id = `item-${index}`;
            const isOpen = openItem === id;

            return (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: index * 0.2 }}
                viewport={{ once: true }}
                className="py-2 border-b border-gray-800/50 last:border-b-0"
              >
                <div
                  onClick={() => toggleItem(id)}
                  className="flex justify-between items-center cursor-pointer text-xl md:text-2xl py-4 font-medium"
                >
                  <h3>{faq.question}</h3>
                  <motion.div
                    animate={{ rotate: isOpen ? 180 : 0 }}
                    transition={{ duration: 0.2 }}
                    className="h-6 w-6 shrink-0"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="24"
                      height="24"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                  </motion.div>
                </div>

                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      key={`content-${id}`}
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="text-lg md:text-xl pb-4 pt-1 text-gray-300">
                        {faq.answer}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
