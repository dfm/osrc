FROM alpine:latest

RUN apk --update add vim redis postgresql-client bash
ADD . /osrc
WORKDIR /osrc

CMD ["bash"]
