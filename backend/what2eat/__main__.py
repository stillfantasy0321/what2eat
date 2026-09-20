import argparse
import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description='Run the what2eat FastAPI service.')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--reload', action='store_true')
    args = parser.parse_args()
    uvicorn.run('what2eat.main:app', host=args.host, port=args.port, reload=args.reload,
                loop='what2eat.runtime:selector_loop_factory')


if __name__ == '__main__':
    main()
