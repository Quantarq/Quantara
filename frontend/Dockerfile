FROM node:20-alpine as build

WORKDIR /app

RUN npm install yarn --global --force

COPY . .

RUN yarn install && yarn build