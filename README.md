# Distributed Systems Project: P2P Auction System

## Introduction

This project is a P2P auction system that allows users to create and participate in auctions. 
The system mimics the real world process closely, where the user is able to take part in auctions and auction off items, while in return contributing with its own computational resources. 
These resources are delegated to replicate the auction system, aiding in holding auctions from other users.

An in-depth explanation of the project can be found in the [project report](doc/report.pdf).

## Architecture

The system is composed of a client and a server. The server is responsible for holding the auctions and the clients are responsible for participating in them. The sever delegates the auctions to the clients, which are responsible for holding the auctions and replicating the system. 

## How to run

First, install the required dependencies by running the following command:

```bash
pip install -r requirements.txt
```

Then, you can run the program by running the following command:

```bash
python  src/main.py
```
## Configuration

The configuration of the system can be found in the `config/config.toml` file. The user can change the configuration of the system by changing the values in this file.
