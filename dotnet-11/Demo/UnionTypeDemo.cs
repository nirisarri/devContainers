namespace UnionTypes;

public static class UnionTypesDemo
{
    public static void Run()
    {
        Console.WriteLine("Union Types Demo");

        Animal[] guests = [
            new Cat("Whiskers"),
            new Bird("Parrot"),
            new Dog("Fido"),
            new Cat("Lulu"),
            new Cat("Tobi"),
        ];

        var report = guests
        .Select((pet, index) => $"{index + 1}. {pet.label}")
        .Prepend("Got a visit from:");

        Console.WriteLine(string.Join(Environment.NewLine, report));
    }
}

record Cat (string Name);
record Dog (string Name);
record Bird(string Species);

union Animal(Cat, Dog, Bird)
{
    public string label => this switch
    {
        Cat cat => $"Cat named {cat.Name}",
        Dog dog => $"Dog named {dog.Name}",
        Bird bird => $"Bird of species {bird.Species}",
        _ => throw new NotImplementedException()
    };
}