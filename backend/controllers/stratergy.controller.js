import { AppDataSource } from "../utils/db.js";

export const saveStrategy = async (req, res) => {
  try {
    const { conditions, userId } = req.body;

    const repo = AppDataSource.getRepository("Strategy");

    let strategy = await repo.findOne({
      where: { user: { user_id: userId } },
      relations: ["user"]
    });

    if (strategy) {
      strategy.conditions = conditions;
    } else {
      strategy = repo.create({
        name: "Default Strategy",
        conditions,
        user: { user_id: userId }
      });
    }

    await repo.save(strategy);

    return res.json({ success: true });

  } catch (err) {
    console.error(err);
    return res.status(500).json({ success: false });
  }
};

export const getStrategy = async (req, res) => {
  try {
    const { userId } = req.params;

    const repo = AppDataSource.getRepository("Strategy");

    const strategy = await repo.findOne({
      where: { user: { user_id: userId } },
      relations: ["user"]
    });

    return res.json({
      success: true,
      conditions: strategy?.conditions || []
    });

  } catch (err) {
    console.error(err);
    return res.status(500).json({ success: false });
  }
};