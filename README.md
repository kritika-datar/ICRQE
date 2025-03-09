# Intelligent Code Review and Quality Enhancement for Software Development
### DISSERTATION
Intelligent Code Review and Quality Enhancement for Software Development (ICRQE) is
developed for developers in any organization to collaborate on a code or code
repository so that they can enhance their productivity by understanding the code faster
and start working on it. ICRQE primarily has the following functionalities: code
documentation generation.
In the developer or software development world when an application is developed it
contains many modules within a code repository. Each module contains functions,
variables and different syntax according to different languages. After the application
initial version is developed, many developers join the team or start working on the code
base. But to understand the code is a big challenge. To go through every piece of code,
every function, every class and doc string takes time. Often this process takes 3-4
weeks and still there are many things which are left unexplored due to human errors.
To provide clear, complete and concise understanding of the code, the Intelligent Code
Review and Quality Enhancement system allows the developer to ask questions related
to the context and understand the code in a better way in less time.
The objective is to provide a solution and implement a platform where all the
requirements of a developer and a team are met. This platform will provide users to
interact with the code in a user-friendly way, giving insights of the technical part of the
code and also eventually provide suggestions to improve the code and thus make the
overall delivery process smoother.

To run the Application:
1. Install requirements from requirements.txt
2. Create directories .repositories and .chroma_db under the backend folder
3. For UI, Install npm and setup react -  npx create-react-app frontend, cd frontend, npm install axios, npm start 
4. To run this project you need and Open AI key. 
5. For running the project pass any python repository url to the text box. And click on Process repository
6. It will generate embeddings and diagrams.
7. Next ask any question relevant to the repository in the text box