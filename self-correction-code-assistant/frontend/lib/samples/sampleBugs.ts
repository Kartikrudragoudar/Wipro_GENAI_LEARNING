import type { SampleBug } from "@/lib/types/loop";

export const fallbackSamples: SampleBug[] = [
  {
    id: "python-typo",
    title: "Python print typo",
    language: "Python",
    code: "def greet(name):\n    pritn(f'Hello, {name}')\n\ngreet('Ada')\n",
    error_message: "NameError: name 'pritn' is not defined",
    user_context: "This fails when running a small greeting script.",
  },
  {
    id: "js-undefined-user",
    title: "JavaScript undefined variable",
    language: "JavaScript",
    code: "function renderGreeting() {\n  console.log(user.name);\n}\n\nrenderGreeting();\n",
    error_message: "ReferenceError: user is not defined",
    user_context: "This is a browser console helper used in onboarding.",
  },
  {
    id: "ts-type-mismatch",
    title: "TypeScript type mismatch",
    language: "TypeScript",
    code: "type Counter = { count: number };\n\nconst state: Counter = { count: '0' as any };\nconsole.log(state.count + 1);\n",
    error_message: "Type 'string' is not assignable to type 'number'",
    user_context: "The counter state should stay numeric.",
  },
  {
    id: "cpp-missing-include",
    title: "C++ missing include",
    language: "C++",
    code: "int main() {\n  cout << \"Ready\";\n  return 0;\n}\n",
    error_message: "error: 'cout' was not declared in this scope",
    user_context: "A tiny command line program does not compile.",
  },
];
