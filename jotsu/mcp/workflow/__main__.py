def main():
    from .server import WorkflowEngine
    engine = WorkflowEngine([])
    engine.run(transport='streamable-http')


if __name__ == '__main__':
    main()
