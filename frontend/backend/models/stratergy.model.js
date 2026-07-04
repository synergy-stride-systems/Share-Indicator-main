import { EntitySchema } from "typeorm";

export const Strategy = new EntitySchema({
  name: "Strategy",
  tableName: "strategies",

  columns: {
    strategy_id: {
      type: "uuid",
      primary: true,
      generated: "uuid",
    },

    name: {
      type: "varchar",
      length: 100,
      default: "Default Strategy"
    },

    conditions: {
      type: "json", // 🔥 store your array here
    },
  },

  relations: {
    user: {
      type: "many-to-one",
      target: "User",
      joinColumn: {
        name: "user_id"
      },
      onDelete: "CASCADE"
    }
  }
});